"""
database/seed_data.py
Inserts realistic sample IPO data so the dashboard is populated on first run.
Run manually: python database/seed_data.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg2
from datetime import date

DB = dict(host="localhost", port=5432, dbname="ipo_db", user="ipo_user", password="ipo_pass")

IPOS = [
    # (name, issue_size, offer_price, list_price, current_price, open, close, listing, sector)
    ("Tata Technologies",    3043.00, 500, 1200, 980,  "2023-11-22", "2023-11-24", "2023-11-30", "Technology"),
    ("IREDA",                2150.21,  32,   50,  220, "2023-11-21", "2023-11-23", "2023-11-29", "Finance"),
    ("Mankind Pharma",       4326.35, 1080, 1300, 2100, "2023-04-25","2023-04-27", "2023-05-09", "Pharma"),
    ("Nexus Select Trust",   3200.00,  100,   96, 130,  "2023-05-09","2023-05-11", "2023-05-19", "Real Estate"),
    ("Zaggle Prepaid",        563.56,  164,  155, 143,  "2023-09-14","2023-09-18", "2023-09-22", "Technology"),
    ("Manoj Vaibhav Gems",    270.44,  215,  221, 190,  "2023-09-13","2023-09-15", "2023-09-20", "Jewellery"),
    ("Concord Biotech",      1551.00,  706,  900, 1640, "2023-08-04","2023-08-07", "2023-08-18", "Pharma"),
    ("EMS",                   321.00,  211,  320, 410,  "2023-10-19","2023-10-23", "2023-10-26", "Infrastructure"),
    ("Droneacharya Aerial",    34.00,   54,   53,  63,  "2022-12-21","2022-12-23", "2022-12-29", "Technology"),
    ("Global Health (Medanta)",2205.57, 336, 401, 870,  "2022-11-03","2022-11-07", "2022-11-16", "Healthcare"),
    ("Archean Chemical",      1462.32,  407,  497, 620, "2022-11-09","2022-11-11", "2022-11-21", "Chemicals"),
    ("Five Star Business",    1960.00,  474,  400, 780, "2022-11-09","2022-11-11", "2022-11-21", "Finance"),
    ("Bikaji Foods",          881.22,   300,  322, 420, "2022-11-03","2022-11-07", "2022-11-16", "FMCG"),
    ("DCX Systems",           500.56,   207,  280, 390, "2022-10-31","2022-11-02", "2022-11-11", "Defence"),
    ("Harsha Engineers",      755.00,   330,  450, 470, "2022-09-14","2022-09-16", "2022-09-26", "Auto Ancillaries"),
    ("Delhivery",            5235.00,   487,  493, 390, "2022-05-11","2022-05-13", "2022-05-24", "Logistics"),
    ("LIC",               21008.48,    949,  867, 770, "2022-05-04","2022-05-09", "2022-05-17", "Finance"),
    ("Paradeep Phosphates",   1501.73,   42,   43,  70, "2022-05-17","2022-05-19", "2022-05-26", "Chemicals"),
    ("Rainbow Children Medicare",1580.77,542,  633, 730,"2022-04-27","2022-04-29", "2022-05-10", "Healthcare"),
    ("Campus Activewear",     1400.00,   292,  380, 260,"2022-04-26","2022-04-28", "2022-05-09", "Retail"),
]

SUBSCRIPTIONS = [
    # (ipo_name, qib, hni, rii, total)
    ("Tata Technologies",    203.41, 62.11,  36.10, 69.43),
    ("IREDA",                 26.04, 31.19,  25.07, 38.80),
    ("Mankind Pharma",        26.61, 17.38,  14.42, 41.62),
    ("Nexus Select Trust",     5.02,  3.14,   1.87,  6.17),
    ("Zaggle Prepaid",        45.22, 37.80,  40.12, 70.30),
    ("Concord Biotech",      174.25, 166.06, 91.70, 24.93),
    ("EMS",                  178.05, 263.17,121.18,157.00),
    ("Global Health (Medanta)",36.53, 45.22, 28.00, 52.00),
    ("Archean Chemical",      55.10, 102.30, 40.50, 68.00),
    ("Five Star Business",    13.20,  11.40,  9.80, 18.00),
    ("Bikaji Foods",          93.20,  73.50, 32.40, 26.66),
    ("DCX Systems",          119.40, 166.00, 81.20,145.00),
    ("Harsha Engineers",     165.52, 225.49,177.47,74.70),
    ("Delhivery",              1.89,  0.42,   1.07,  1.63),
    ("LIC",                    2.83,  2.91,   1.99,  2.95),
    ("Rainbow Children Medicare",79.90,108.22,57.30,92.00),
    ("Campus Activewear",     22.01, 10.80,  14.20, 51.75),
]


def seed():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    name_to_id = {}
    for row in IPOS:
        (name, issue_size, offer_price, list_price, current_price,
         open_d, close_d, listing_d, sector) = row

        listing_gain = round((list_price - offer_price) / offer_price * 100, 2)
        current_gain = round((current_price - offer_price) / offer_price * 100, 2)

        cur.execute("""
            INSERT INTO ipo_master
                (ipo_name, issue_size, offer_price, list_price, current_price,
                 listing_gain, current_gain, open_date, close_date, listing_date,
                 sector, exchange)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (ipo_name) DO UPDATE SET
                list_price    = EXCLUDED.list_price,
                current_price = EXCLUDED.current_price,
                listing_gain  = EXCLUDED.listing_gain,
                current_gain  = EXCLUDED.current_gain,
                updated_at    = NOW()
            RETURNING ipo_id
        """, (name, issue_size, offer_price, list_price, current_price,
              listing_gain, current_gain, open_d, close_d, listing_d,
              sector, "NSE"))
        name_to_id[name] = cur.fetchone()[0]

    for row in SUBSCRIPTIONS:
        name, qib, hni, rii, total = row
        ipo_id = name_to_id.get(name)
        if ipo_id:
            cur.execute("""
                INSERT INTO ipo_subscription (ipo_id, qib, hni, rii, total_subscription)
                VALUES (%s,%s,%s,%s,%s)
            """, (ipo_id, qib, hni, rii, total))

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅  Seeded {len(IPOS)} IPOs and {len(SUBSCRIPTIONS)} subscription records.")


if __name__ == "__main__":
    seed()
