import google.generativeai as genai
import sqlite3
import csv
import os
from datetime import datetime

# ─────────────────────────────────────────
#  PUT YOUR GEMINI API KEY HERE
API_KEY = ""
# Get free key from: https://aistudio.google.com/app/apikey
# ─────────────────────────────────────────

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

DB_FILE = "expenses.db"
CATEGORIES = ["food", "travel", "study", "rent", "entertainment", "health", "other"]

# ── DATABASE ──
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            date     TEXT,
            type     TEXT,
            category TEXT,
            amount   REAL,
            note     TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_transaction():
    print("\n  Type: 1=Income  2=Expense")
    t = input("  Choose (1/2): ").strip()
    type_ = "income" if t == "1" else "expense"

    try:
        amount = float(input("  Amount (₹): ").strip())
    except ValueError:
        print("  ❌ Invalid amount.")
        return

    if type_ == "expense":
        print(f"  Categories: {', '.join(CATEGORIES)}")
        category = input("  Category: ").strip().lower()
        if category not in CATEGORIES:
            category = "other"
    else:
        category = "income"

    note = input("  Note (optional): ").strip()
    date = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO transactions (date, type, category, amount, note) VALUES (?, ?, ?, ?, ?)",
        (date, type_, category, amount, note)
    )
    conn.commit()
    conn.close()
    print(f"  ✅ ₹{amount:.0f} {type_} ({category}) saved!\n")

def monthly_summary():
    month = input("\n  Enter month (YYYY-MM, e.g. 2025-05) or press Enter for current: ").strip()
    if not month:
        month = datetime.now().strftime("%Y-%m")

    conn = sqlite3.connect(DB_FILE)

    # Total income & expense
    totals = conn.execute("""
        SELECT type, SUM(amount) FROM transactions
        WHERE strftime('%Y-%m', date) = ?
        GROUP BY type
    """, (month,)).fetchall()

    # Category breakdown
    cats = conn.execute("""
        SELECT category, SUM(amount) as total FROM transactions
        WHERE type='expense' AND strftime('%Y-%m', date) = ?
        GROUP BY category ORDER BY total DESC
    """, (month,)).fetchall()
    conn.close()

    print(f"\n  ── SUMMARY: {month} ──")
    income = expense = 0
    for t, amt in totals:
        if t == "income":
            income = amt
        else:
            expense = amt
    print(f"  💰 Total Income : ₹{income:.0f}")
    print(f"  💸 Total Expense: ₹{expense:.0f}")
    print(f"  🏦 Net Savings  : ₹{income - expense:.0f}")

    if cats:
        print(f"\n  ── EXPENSES BY CATEGORY ──")
        for cat, amt in cats:
            bar = "█" * int(amt / max(c[1] for c in cats) * 20)
            print(f"  {cat:<15} ₹{amt:>7.0f}  {bar}")
    print()
    return month, income, expense, cats

def get_ai_insights():
    month, income, expense, cats = monthly_summary()
    if expense == 0:
        print("  No expense data found for this month.\n")
        return

    summary_text = f"Month: {month}\nTotal Income: ₹{income:.0f}\nTotal Expense: ₹{expense:.0f}\nSavings: ₹{income-expense:.0f}\n\nCategory Breakdown:\n"
    for cat, amt in cats:
        pct = (amt / expense * 100) if expense else 0
        summary_text += f"  {cat}: ₹{amt:.0f} ({pct:.1f}%)\n"

    print("  🤖 Getting AI advice...\n")
    prompt = f"""You are a friendly financial advisor for a college student in India.

Here is their monthly expense data:
{summary_text}

Give:
1. 🔴 Top 2 overspending areas with reason
2. 💡 3 practical tips to save money next month (India-specific)
3. 🎯 A realistic savings goal for next month

Be friendly, specific, and under 200 words. Use ₹ for amounts."""

    resp = model.generate_content(prompt)
    print("="*45)
    print("  🤖 AI ADVISOR SAYS:")
    print("="*45)
    print(resp.text)
    print("="*45 + "\n")

def export_csv():
    month = input("\n  Export which month? (YYYY-MM or Enter for all): ").strip()
    conn = sqlite3.connect(DB_FILE)
    if month:
        rows = conn.execute(
            "SELECT date, type, category, amount, note FROM transactions WHERE strftime('%Y-%m', date) = ?",
            (month,)
        ).fetchall()
        fname = f"expenses_{month}.csv"
    else:
        rows = conn.execute("SELECT date, type, category, amount, note FROM transactions").fetchall()
        fname = "expenses_all.csv"
    conn.close()

    if not rows:
        print("  No data found.\n")
        return
    with open(fname, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Type", "Category", "Amount (₹)", "Note"])
        writer.writerows(rows)
    print(f"  ✅ Exported {len(rows)} records to {fname}\n")

# ── MAIN MENU ──
def main():
    init_db()
    print("\n" + "="*45)
    print("     💰 SMART EXPENSE TRACKER")
    print("     by Omkar Kumar")
    print("="*45)

    while True:
        print("\n  1. Add income / expense")
        print("  2. View monthly summary")
        print("  3. Get AI spending insights 🤖")
        print("  4. Export to CSV")
        print("  5. Exit")
        choice = input("\n  Choose (1-5): ").strip()

        if choice == "1":
            add_transaction()
        elif choice == "2":
            monthly_summary()
        elif choice == "3":
            get_ai_insights()
        elif choice == "4":
            export_csv()
        elif choice == "5":
            print("\n  Goodbye! Save more! 💪\n")
            break
        else:
            print("  Invalid choice. Try again.")

if __name__ == "__main__":
    main()
