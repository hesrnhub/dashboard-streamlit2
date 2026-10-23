from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------
# Konfigurasi halaman
# ---------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Penjualan Cafe 2023",
    page_icon="☕",
    layout="wide",
)

DATA_PATH = Path(__file__).parent / "cafe_sales_clean.csv"
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"]
UNKNOWN = "Tidak Diketahui"

# Palet warna bertema kopi (satu warna utama + aksen)
BROWN = "#6F4E37"
CARAMEL = "#C68B59"
COLORS = ["#6F4E37", "#C68B59", "#A9714B", "#3E2A1E", "#D9B99B", "#8C6A4F"]


# ---------------------------------------------------------------
# Memuat data
# ---------------------------------------------------------------
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["Transaction Date"])
    df["Month"] = df["Month"].astype("Int64")
    return df


df = load_data()

# ---------------------------------------------------------------
# Judul dan deskripsi
# ---------------------------------------------------------------
st.title("☕ Dashboard Penjualan Cafe 2023")
st.markdown(
    "Dashboard interaktif untuk menganalisis **10.000 transaksi** sebuah cafe "
    "sepanjang tahun 2023: menu apa yang paling menghasilkan pendapatan, kapan "
    "penjualan ramai, dan bagaimana pelanggan membayar. "
    "Gunakan filter di sidebar untuk menyaring data. Semua KPI dan grafik "
    "akan ikut berubah."
)

# ---------------------------------------------------------------
# Filter interaktif (sidebar)
# ---------------------------------------------------------------
st.sidebar.header("Filter Data")

min_date = df["Transaction Date"].min().date()
max_date = df["Transaction Date"].max().date()
date_range = st.sidebar.date_input(
    "Rentang tanggal",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
include_nodate = st.sidebar.checkbox(
    "Sertakan transaksi tanpa tanggal", value=True,
    help="460 transaksi tidak punya tanggal valid. "
         "Tetap dihitung di KPI, tetapi tidak muncul di grafik tren waktu.",
)

items = sorted(df["Item"].unique())
sel_items = st.sidebar.multiselect("Menu (Item)", items, default=items)

locations = sorted(df["Location"].unique())
sel_loc = st.sidebar.multiselect("Lokasi", locations, default=locations)

payments = sorted(df["Payment Method"].unique())
sel_pay = st.sidebar.multiselect("Metode pembayaran", payments, default=payments)

#mengembalikan 1 tanggal saat user baru memilih tanggal awal
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start, end = date_range
else:
    start, end = min_date, max_date

in_range = df["Transaction Date"].between(pd.Timestamp(start), pd.Timestamp(end))
if include_nodate:
    in_range = in_range | df["Transaction Date"].isna()

mask = (
    in_range
    & df["Item"].isin(sel_items)
    & df["Location"].isin(sel_loc)
    & df["Payment Method"].isin(sel_pay)
)
fdf = df[mask]

if fdf.empty:
    st.warning("Tidak ada data yang cocok dengan filter. Longgarkan filter di sidebar.")
    st.stop()

# ---------------------------------------------------------------
# KPI
# ---------------------------------------------------------------
total_revenue = fdf["Total Spent"].sum()
n_trx = len(fdf)
avg_trx = fdf["Total Spent"].mean()
items_sold = int(fdf["Quantity"].sum())

known = fdf[fdf["Item"] != UNKNOWN]
if known.empty:
    top_item, top_item_rev = "-", 0.0
else:
    by_item = known.groupby("Item")["Total Spent"].sum()
    top_item, top_item_rev = by_item.idxmax(), by_item.max()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Pendapatan", f"${total_revenue:,.0f}")
k2.metric("Jumlah Transaksi", f"{n_trx:,}")
k3.metric("Rata-rata per Transaksi", f"${avg_trx:,.2f}")
k4.metric("Total Item Terjual", f"{items_sold:,}")
k5.metric("Menu Terlaris", top_item,
          help="Menu dengan total pendapatan tertinggi (tanpa 'Tidak Diketahui').")
k5.caption(f"Pendapatan ${top_item_rev:,.0f}")

st.divider()


def style(fig, height=380):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        title_font_size=16,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ---------------------------------------------------------------
# Baris 1: Bar chart + Line chart
# ---------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    rev_item = (fdf.groupby("Item", as_index=False)["Total Spent"].sum()
                .sort_values("Total Spent"))
    fig = px.bar(rev_item, x="Total Spent", y="Item", orientation="h",
                 text_auto=",.0f", title="Pendapatan per Menu",
                 labels={"Total Spent": "Pendapatan ($)", "Item": ""})
    fig.update_traces(marker_color=BROWN)
    st.plotly_chart(style(fig), width="stretch")

with c2:
    dated = fdf.dropna(subset=["Month"])
    monthly = (dated.groupby("Month", as_index=False)["Total Spent"].sum()
               .sort_values("Month"))
    monthly["Bulan"] = monthly["Month"].map(lambda m: MONTH_LABELS[int(m) - 1])
    fig = px.line(monthly, x="Bulan", y="Total Spent", markers=True,
                  title="Tren Pendapatan Bulanan",
                  labels={"Total Spent": "Pendapatan ($)", "Bulan": ""})
    fig.update_traces(line_color=BROWN, marker_color=CARAMEL, marker_size=9)
    fig.update_xaxes(categoryorder="array", categoryarray=MONTH_LABELS)
    fig.update_yaxes(range=[0, monthly["Total Spent"].max() * 1.15])
    st.plotly_chart(style(fig), width="stretch")

# ---------------------------------------------------------------
# Baris 2: Pie chart + Histogram
# ---------------------------------------------------------------
c3, c4 = st.columns(2)

with c3:
    pay = fdf.groupby("Payment Method", as_index=False)["Total Spent"].sum()
    fig = px.pie(pay, names="Payment Method", values="Total Spent", hole=0.45,
                 title="Porsi Pendapatan per Metode Pembayaran",
                 color_discrete_sequence=COLORS)
    fig.update_traces(textinfo="percent+label")
    st.plotly_chart(style(fig), width="stretch")

with c4:
    fig = px.histogram(fdf, x="Total Spent", nbins=20,
                       title="Distribusi Nilai Transaksi",
                       labels={"Total Spent": "Nilai transaksi ($)"})
    fig.update_traces(marker_color=CARAMEL)
    fig.update_layout(yaxis_title="Jumlah transaksi", bargap=0.05)
    st.plotly_chart(style(fig), width="stretch")

# ---------------------------------------------------------------
# Baris 3: Heatmap (lebar penuh) + perbandingan lokasi
# ---------------------------------------------------------------
c5, c6 = st.columns([2, 1])

with c5:
    heat = dated.pivot_table(index="Weekday", columns="Month",
                             values="Total Spent", aggfunc="sum")
    heat = heat.reindex(index=WEEKDAYS)
    heat.columns = [MONTH_LABELS[int(m) - 1] for m in heat.columns]
    heat = heat.reindex(columns=[m for m in MONTH_LABELS if m in heat.columns])
    fig = px.imshow(heat, aspect="auto", text_auto=",.0f",
                    color_continuous_scale=["#F5E9DD", CARAMEL, "#3E2A1E"],
                    title="Heatmap Pendapatan: Hari × Bulan",
                    labels=dict(color="Pendapatan ($)"))
    st.plotly_chart(style(fig, 420), width="stretch")

with c6:
    loc = fdf.groupby("Location", as_index=False)["Total Spent"].sum()
    fig = px.bar(loc, x="Location", y="Total Spent", text_auto=",.0f",
                 title="Pendapatan per Lokasi",
                 labels={"Total Spent": "Pendapatan ($)", "Location": ""})
    fig.update_traces(marker_color=BROWN)
    st.plotly_chart(style(fig, 420), width="stretch")

# ---------------------------------------------------------------
# Catatan data & tabel
# ---------------------------------------------------------------
st.divider()
with st.expander("Catatan kualitas data"):
    n_unknown_item = int((fdf["Item"] == UNKNOWN).sum())
    n_unknown_pay = int((fdf["Payment Method"] == UNKNOWN).sum())
    n_unknown_loc = int((fdf["Location"] == UNKNOWN).sum())
    n_nodate = int(fdf["Transaction Date"].isna().sum())
    st.markdown(
        f"Pada data yang sedang ditampilkan:\n"
        f"- **{n_unknown_item:,}** transaksi bermenu *{UNKNOWN}*\n"
        f"- **{n_unknown_pay:,}** transaksi bermetode bayar *{UNKNOWN}*\n"
        f"- **{n_unknown_loc:,}** transaksi berlokasi *{UNKNOWN}*\n"
        f"- **{n_nodate:,}** transaksi tanpa tanggal "
        f"(tidak tampil di tren bulanan dan heatmap)\n\n"
        "Nilai `ERROR`, `UNKNOWN`, dan sel kosong pada data asli sudah diubah "
        "menjadi data hilang, lalu dipulihkan dengan rumus "
        "*Total = Quantity × Price* bila memungkinkan."
    )

with st.expander("Lihat data transaksi"):
    st.dataframe(fdf, width="stretch", hide_index=True)
    st.download_button("Unduh data terfilter (CSV)",
                       fdf.to_csv(index=False).encode("utf-8"),
                       file_name="cafe_sales_filtered.csv", mime="text/csv")
