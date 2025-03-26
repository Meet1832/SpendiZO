-- Create budgets table
CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    period TEXT NOT NULL,
    start_date TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);