from flask import Flask, render_template, request, redirect, session, url_for, flash
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from alpha_vantage.fundamentaldata import FundamentalData
from stocknews import StockNews
import ollama
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Alpha Vantage API Key
ALPHA_VANTAGE_API_KEY = "your_alpha_vantage_api_key"

# Initialize Fundamental Data
fd = FundamentalData(key=ALPHA_VANTAGE_API_KEY, output_format="pandas")

# Routes
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    users_file = "users.csv"
    if not os.path.exists(users_file):
        pd.DataFrame(columns=["name", "email", "username", "password"]).to_csv(users_file, index=False)

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        if not name or not email or not username or not password:
            flash("All fields are required!", "error")
        else:
            user_data = pd.read_csv(users_file)
            if username in user_data["username"].values:
                flash("Username already exists!", "error")
            else:
                new_user = pd.DataFrame({"name": [name], "email": [email], "username": [username], "password": [password]})
                user_data = pd.concat([user_data, new_user], ignore_index=True)
                user_data.to_csv(users_file, index=False)
                flash("Sign-up successful! Please log in.", "success")
                return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    users_file = "users.csv"
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user_data = pd.read_csv(users_file)

        if (username in user_data["username"].values) and (
            password == user_data[user_data["username"] == username]["password"].values[0]
        ):
            session["authenticated"] = True
            session["current_user"] = username
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password!", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("home"))


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "authenticated" not in session or not session["authenticated"]:
        flash("You need to log in to access the dashboard!", "error")
        return redirect(url_for("login"))

    candlestick_plot = None
    financials = {}
    news_articles = []
    ai_analysis = None

    if request.method == "POST":
        ticker = request.form.get("ticker")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        indicators = request.form.getlist("indicators")

        if "fetch_data" in request.form:
            try:
                # Fetch stock data
                stock_data = yf.download(ticker, start=start_date, end=end_date)
                if stock_data.empty:
                    flash("No data available for the specified ticker and date range.", "error")
                else:
                    # Generate candlestick plot
                    candlestick_plot = generate_candlestick_plot(stock_data, indicators)
                    # Fetch financial data
                    financials = fetch_financial_data(ticker)
                    # Fetch stock news
                    news_articles = fetch_stock_news(ticker)
            except Exception as e:
                flash(f"Error fetching data: {e}", "error")

        if "ai_analysis" in request.form:
            try:
                # Run AI analysis
                ai_analysis = run_ai_analysis()
            except Exception as e:
                flash(f"Error during AI analysis: {e}", "error")

    return render_template(
        "dashboard.html",
        candlestick_plot=candlestick_plot,
        financials=financials,
        news_articles=news_articles,
        ai_analysis=ai_analysis,
    )


# Utility Functions
def generate_candlestick_plot(stock_data, indicators):
    """Generate a candlestick plot with optional indicators."""
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=stock_data.index,
                open=stock_data["Open"],
                high=stock_data["High"],
                low=stock_data["Low"],
                close=stock_data["Close"],
            )
        ]
    )

    # Add indicators
    if "SMA" in indicators:
        stock_data["SMA"] = stock_data["Close"].rolling(window=20).mean()
        fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data["SMA"], mode="lines", name="20-Day SMA"))

    if "EMA" in indicators:
        stock_data["EMA"] = stock_data["Close"].ewm(span=20).mean()
        fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data["EMA"], mode="lines", name="20-Day EMA"))

    fig.update_layout(xaxis_rangeslider_visible=False)
    return fig.to_html(full_html=False)


def fetch_financial_data(ticker):
    """Fetch financial data using Alpha Vantage API."""
    financials = {}
    try:
        balance_sheet, _ = fd.get_balance_sheet_annual(ticker)
        income_statement, _ = fd.get_income_statement_annual(ticker)
        financials["Balance Sheet"] = balance_sheet.to_html(classes="table table-striped")
        financials["Income Statement"] = income_statement.to_html(classes="table table-striped")
    except Exception as e:
        financials["Error"] = f"Unable to fetch financial data: {e}"
    return financials


def fetch_stock_news(ticker):
    """Fetch stock-related news articles."""
    news = StockNews(ticker, save_news=False)
    return [{"title": article["title"], "link": article["url"]} for article in news.get_news()[:5]]


def run_ai_analysis():
    """Run AI-powered stock analysis using Ollama."""
    messages = [
        {"role": "user", "content": "Analyze the stock chart and provide a buy/hold/sell recommendation."}
    ]
    response = ollama.chat(model="llama3.2-vision", messages=messages)
    return response["message"]["content"]


if __name__ == "__main__":
    app.run(debug=True)
