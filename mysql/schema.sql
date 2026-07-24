CREATE TABLE companies (
    ticker VARCHAR(10) PRIMARY KEY,
    name   VARCHAR(100) NOT NULL,
    sector VARCHAR(100) NOT NULL
);

CREATE TABLE stocks (
    ticker VARCHAR(10)  NOT NULL,
    date   DATE         NOT NULL,
    high   FLOAT        NOT NULL,
    low    FLOAT        NOT NULL,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES companies(ticker)
);
