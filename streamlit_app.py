import streamlit as st
import math
import pandas as pd
import altair as alt

###############################################################################
# 1) PRICE-LEVEL CONSTRUCTION
###############################################################################
def build_price_levels(start_price, end_price, interval_type, interval_value):
    """
    Build a descending list of prices from start_price down to end_price,
    using either fixed dollar steps or percentage drops from the previous level.
    Rounds each price to 2 decimals.
    """
    prices = []
    current_price = start_price

    if start_price <= end_price:
        st.warning("Starting price must be ABOVE the Lowest Expected Price.")
        return [round(start_price, 2)]
    
    if interval_value <= 0:
        st.warning("Interval value must be positive.")
        return [round(start_price, 2), round(end_price, 2)]
    
    prices.append(current_price)
    
    while True:
        if interval_type == "$":
            next_price = current_price - interval_value
        else:  # percentage
            next_price = current_price * (1 - interval_value)
        
        if next_price <= end_price:
            break
        prices.append(next_price)
        current_price = next_price
    
    prices.append(end_price)
    
    # Round to 2 decimals
    return [round(p, 2) for p in prices]

###############################################################################
# 2) ALLOCATION / BUY-SIZING LOGIC
###############################################################################
def find_optimal_allocation(prices, budget, avg_cost_margin, max_Q0_search=10000):
    """
    Finds the largest feasible Q0 (initial shares) such that for each subsequent
    price P_i, you buy enough shares to keep average cost <= (1 + avg_cost_margin)*P_i,
    without exceeding the total 'budget'.
    """
    best_Q0 = 0
    best_solution = None
    
    for Q0 in range(max_Q0_search + 1):
        Q = [0]*len(prices)
        Q[0] = Q0
        
        S_price = prices[0] * Q0
        S_shares = Q0
        
        for i in range(1, len(prices)):
            p_i = prices[i]
            lhs = S_price - (1 + avg_cost_margin)*p_i*S_shares
            denom = avg_cost_margin * p_i

            min_needed = lhs / denom if denom != 0 else 0
            if min_needed < 0:
                min_needed = 0
            
            buy_i = math.ceil(min_needed)
            Q[i] = buy_i
            
            S_price += p_i * buy_i
            S_shares += buy_i
        
        total_cost = sum(p*q for p,q in zip(prices, Q))
        if total_cost <= budget:
            if Q0 > best_Q0:
                best_Q0 = Q0
                best_solution = (Q, total_cost)
    
    return best_solution

###############################################################################
# 3) BUILD DATAFRAMES
###############################################################################
def build_display_df(prices, shares):
    """
    DataFrame for display (no 'Price_str' column).
    """
    rows = []
    S_price = 0.0
    S_shares = 0
    cum_invest = 0.0
    
    for p, q in zip(prices, shares):
        cost = p * q
        S_price += cost
        S_shares += q
        
        avg_cost = (S_price / S_shares) if S_shares>0 else 0.0
        
        diff_vs_avg = 0.0
        if avg_cost != 0:
            diff_vs_avg = ((p - avg_cost)/avg_cost)*100
        
        cum_invest += cost
        
        rows.append({
            "Price": round(p, 2),
            "Shares Purchased": q,
            "Average Purchase Price": round(avg_cost, 2),
            "% Diff (Current vs. Avg)": round(diff_vs_avg, 2),
            "Cost of Purchase": round(cost, 2),
            "Cumulative Investment": round(cum_invest, 2),
            "Cumulative Shares": S_shares
        })
    return pd.DataFrame(rows)


def build_chart_df(prices, shares):
    """
    DataFrame for charts only. We copy the % Diff column to a new column
    named 'pctDiffCurVsAvg' that doesn't contain '%'.
    """
    disp_df = build_display_df(prices, shares).copy()
    
    # Create a new column for the Altair x-axis labels
    disp_df["Price_str"] = disp_df["Price"].apply(lambda x: f"{x:.2f}")
    
    # Copy data from "% Diff (Current vs. Avg)" to 'pctDiffCurVsAvg'
    disp_df["pctDiffCurVsAvg"] = disp_df["% Diff (Current vs. Avg)"]
    
    return disp_df

###############################################################################
# 4) STREAMLIT APP
###############################################################################
def main():
    st.title("Buy-the-Dip Strategy Simulator")

    budget = st.number_input(
        "Total Investment Budget ($)",
        value=100000,
        min_value=0,
        step=1000,
        format="%d"
    )
    start_price = st.number_input("Starting Stock Price ($)", value=75.0, min_value=0.01, step=0.5)
    end_price = st.number_input("Lowest Expected Stock Price ($)", value=60.0, min_value=0.0, step=0.5)

    interval_type = st.radio("Interval Type", options=["$", "%"], horizontal=True)
    if interval_type == "$":
        interval_value = st.number_input("Interval Value ($)", value=2.50, step=0.5, min_value=0.0)
    else:
        interval_percent = st.number_input("Interval Value (%)", value=5.0, step=1.0, min_value=0.01)
        interval_value = interval_percent / 100.0

    # Renamed label
    margin_pct = st.number_input("Average cost must stay within (%) of last price", value=2.0, step=0.5, min_value=0.0)
    margin = margin_pct / 100.0

    if st.button("Run Simulation"):
        prices = build_price_levels(start_price, end_price, interval_type, interval_value)
        result = find_optimal_allocation(prices, budget, avg_cost_margin=margin)
        
        if not result:
            st.error("No feasible solution found with these parameters.")
            return
        
        Q, total_spent = result
        st.success(f"Feasible Solution Found — Total Spent: ${round(total_spent,2):,}")

        # Build two separate DataFrames:
        # 1) df for display, 2) chart_df for altair
        df = build_display_df(prices, Q)
        chart_df = build_chart_df(prices, Q)
        
        # Show the user only df
        st.dataframe(df)

        #####################################################################
        # CHART #1: SHARES PURCHASED & INVESTMENT
        #####################################################################
        base = alt.Chart(chart_df).encode(
            x=alt.X(
                "Price_str:N",
                sort=None,
                title="Price",
                axis=alt.Axis(labelFontSize=16, titleFontSize=16)
            )
        )
        
        bar_shares = base.mark_bar(color="lightblue", opacity=0.6).encode(
            y=alt.Y(
                "Shares Purchased:Q", 
                axis=alt.Axis(title="Shares Purchased (Bar)", labelFontSize=16, titleFontSize=16)
            ),
            tooltip=["Shares Purchased", "Cumulative Shares", "Price"]
        )
        
        line_invest = base.mark_line(point=True, stroke="green", strokeWidth=3).encode(
            y=alt.Y(
                "Cumulative Investment:Q",
                axis=alt.Axis(
                    title="Cumulative Investment ($)",
                    titleColor="green",
                    labelFontSize=16, 
                    titleFontSize=16
                ),
                scale=alt.Scale(zero=False)
            ),
            tooltip=["Cumulative Investment", "Price"]
        )

        shares_invest_chart = alt.layer(
            bar_shares,
            line_invest
        ).resolve_scale(y='independent').properties(
            width=700,
            height=400,
            title="Shares Purchased & Investment Over Price Levels"
        )
        
        st.altair_chart(shares_invest_chart, use_container_width=True)

        #####################################################################
        # CHART #2: CUMULATIVE SHARES
        #####################################################################
        chart_cum_shares = (
            alt.Chart(chart_df)
            .mark_line(point=True, color="blue", strokeWidth=3)
            .encode(
                x=alt.X(
                    "Price_str:N",
                    sort=None,
                    title="Price",
                    axis=alt.Axis(labelFontSize=16, titleFontSize=16)
                ),
                y=alt.Y(
                    "Cumulative Shares:Q",
                    title="Cumulative Shares",
                    axis=alt.Axis(labelFontSize=16, titleFontSize=16),
                    scale=alt.Scale(zero=False)
                ),
                tooltip=["Cumulative Shares", "Price"]
            )
            .properties(width=700, height=400, title="Cumulative Shares vs. Price")
        )
        st.altair_chart(chart_cum_shares, use_container_width=True)

        #####################################################################
        # CHART #3: AVERAGE PURCHASE PRICE
        #####################################################################
        chart_avg_cost = (
            alt.Chart(chart_df)
            .mark_line(point=True, color="red", strokeWidth=3)
            .encode(
                x=alt.X(
                    "Price_str:N",
                    sort=None,
                    title="Price",
                    axis=alt.Axis(labelFontSize=16, titleFontSize=16)
                ),
                y=alt.Y(
                    "Average Purchase Price:Q",
                    title="Avg. Purchase Price ($)",
                    axis=alt.Axis(labelFontSize=16, titleFontSize=16),
                    scale=alt.Scale(zero=False)
                ),
                tooltip=["Average Purchase Price", "Price"]
            )
            .properties(width=700, height=400, title="Average Purchase Price vs. Price")
        )
        st.altair_chart(chart_avg_cost, use_container_width=True)

        #####################################################################
        # CHART #4: % DIFF (CURRENT vs. AVG) with dynamic domain
        #####################################################################
        # Compute domain for the y-axis as before
        min_diff = chart_df["pctDiffCurVsAvg"].min()
        max_diff = chart_df["pctDiffCurVsAvg"].max()
        if min_diff == max_diff:
            domain = [min_diff - 1, max_diff + 1]
        else:
            pad = 0.2 * (max_diff - min_diff)
            domain = [min_diff - pad, max_diff + pad]

        # Build a reversed list of Price_str values
        sorted_prices = sorted(chart_df["Price_str"].unique(), 
                            key=lambda x: float(x), 
                            reverse=True)

        pct_diff_line = alt.Chart(chart_df).mark_line(
            stroke="purple", strokeWidth=4
        ).encode(
            x=alt.X(
                "Price_str:N",
                sort=sorted_prices,  # <--- reversed numeric order
                title="Price"
            ),
            y=alt.Y(
                "pctDiffCurVsAvg:Q",
                title="% Diff (Cur vs Avg)",
                scale=alt.Scale(domain=domain, nice=False)
            ),
            tooltip=["Price", "pctDiffCurVsAvg"]
        )

        pct_diff_circles = alt.Chart(chart_df).mark_circle(
            color="purple", size=100
        ).encode(
            x=alt.X("Price_str:N", sort=sorted_prices),
            y="pctDiffCurVsAvg:Q",
            tooltip=["Price", "pctDiffCurVsAvg"]
        )

        pct_diff_chart = alt.layer(
            pct_diff_line, pct_diff_circles
        ).properties(
            width=700, height=400,
            title="% Diff: Current Price vs. Average Purchase Price"
        )

        st.altair_chart(pct_diff_chart, use_container_width=True)

if __name__ == "__main__":
    main()