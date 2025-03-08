# DCA "Buy-the-Dip" Strategy Simulator

This Streamlit app demonstrates a **Dollar-Cost Averaging (DCA) approach** for buying a stock (or ETF) in **incremental “dip” intervals**. It lets you specify:

1. Your **total investment budget**  
2. The **starting stock price** (and a lowest potential dip price)  
3. **Interval spacing** (either fixed-dollar or fixed-percentage steps)  
4. How closely your **average cost** should stay to each newly-lowered price  

Based on these settings, the app calculates:
- How many shares you can initially buy, and
- How many additional shares to buy at each dip level,  
while respecting your total budget and your average-cost constraints.

---

## How to Use

1. **Try the live demo**:  
   [https://dcastrat.streamlit.app/](https://dcastrat.streamlit.app/)

2. **Run Locally**:

   1. **Install Requirements**:
      ```bash
      pip install -r requirements.txt
      ```

   2. **Run the App**:
      ```bash
      streamlit run streamlit_app.py
      ```