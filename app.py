"""
The 2026 Escalation in the Middle East – interactive presentation dashboard.
Run with:  streamlit run app.py
Data: ACLED Middle East aggregated data (weekly), https://acleddata.com
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = Path(__file__).parent / "Middle-East_aggregated_data_up_to_week_of-2026-11-07.xlsx"

# ---------- style ----------
C2025, C2026 = "#9aa3ad", "#eb6834"
TYPE_COLORS = {
    "Protests": "#2a78d6", "Riots": "#eb6834", "Explosions/Remote violence": "#1baf7a",
    "Battles": "#eda100", "Violence against civilians": "#e87ba4", "Strategic developments": "#6250d6",
}
TYPES = list(TYPE_COLORS)
GULF = ["Saudi Arabia", "United Arab Emirates", "Kuwait", "Bahrain", "Qatar", "Oman"]
SEAS = ["Mediterranean Sea", "Indian Ocean"]
ESCALATION = pd.Timestamp("2026-02-28")
IRAN_JAN = pd.Timestamp("2026-01-03")
SEQ_BLUE = [[0, "#f4f7fb"], [0.33, "#a9c8ee"], [0.66, "#2a78d6"], [1, "#0f3f7a"]]

st.set_page_config(page_title="Middle East 2026 Escalation", page_icon="📊", layout="wide")


def style(fig, height=430):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=40, b=10), template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        hoverlabel=dict(bgcolor="white"), font=dict(size=13),
    )
    fig.update_xaxes(showgrid=False)
    return fig


# ---------- data ----------
@st.cache_data(show_spinner="Loading ACLED data …")
def load():
    # Reading the Excel file takes ~30 s, so the 2025–2026 subset is cached as a fast Parquet file after the first run.
    cache = DATA_PATH.with_name("acled_2025_2026_cache.parquet")
    if cache.exists() and cache.stat().st_mtime > DATA_PATH.stat().st_mtime:
        df = pd.read_parquet(cache)
    else:
        df = pd.read_excel(DATA_PATH)
        df = df[df["WEEK"] >= "2025-01-01"].reset_index(drop=True)
        df.to_parquet(cache)
    df = df.copy()
    df["YEAR"] = df["WEEK"].dt.year
    df["WEEK_NO"] = df.groupby("YEAR")["WEEK"].transform(lambda w: (w - w.min()).dt.days // 7 + 1)
    return df


df = load()
N_WEEKS = int(df.loc[df["YEAR"] == 2026, "WEEK_NO"].max())
cmp_ = df[df["WEEK_NO"] <= N_WEEKS]
ALL_COUNTRIES = sorted(c for c in df["COUNTRY"].unique() if c not in SEAS)

# ---------- header ----------
st.title("The 2026 Escalation in the Middle East")
st.caption(f"ACLED weekly conflict data · {len(df):,} rows · Jan 2025 – {df['WEEK'].max():%d %b %Y} · "
           f"year comparisons use weeks 1–{N_WEEKS} of each year")

y = cmp_.groupby("YEAR")[["EVENTS", "FATALITIES"]].sum()
gulf_ev = df[df["COUNTRY"].isin(GULF) & (df["EVENT_TYPE"] == "Explosions/Remote violence")].groupby("YEAR")["EVENTS"].sum()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Events 2026", f"{y.loc[2026, 'EVENTS']:,}", f"{y.loc[2026, 'EVENTS'] / y.loc[2025, 'EVENTS'] - 1:+.0%} vs 2025")
k2.metric("Reported fatalities 2026", f"{y.loc[2026, 'FATALITIES']:,}",
          f"{y.loc[2026, 'FATALITIES'] / y.loc[2025, 'FATALITIES'] - 1:+.0%} vs 2025", delta_color="inverse")
k3.metric("Escalation week", "28 Feb 2026", "events ×2.4 in 6 weeks", delta_color="off", delta_arrow="off")
k4.metric("Gulf strike events 2026", f"{gulf_ev.get(2026, 0):,}", f"{gulf_ev.get(2025, 0)} in 2025", delta_color="off", delta_arrow="off")

tabs = st.tabs(["Overview", "Q1 · Timing", "Q2 · Countries", "Q3 · Iran", "Q4 · Gulf spillover",
                "Q5 · Lethality", "Map", "Conclusion"])

# ---------- Overview ----------
with tabs[0]:
    a, b = st.columns([3, 2])
    with a:
        st.subheader("What is this project about?")
        st.markdown("""
2026 began with a deadly wave of unrest in Iran. From the end of February the data shows a sharp rise in air, drone and
missile strikes, which also reached the Gulf states. This dashboard uses **2025 as a baseline** to measure
**when** the escalation started, **where** it happened, **how** the type of violence changed and **how deadly** it was.

**Research questions**
1. **Timing:** How did weekly events and fatalities in 2026 compare with 2025, and when did the escalation start?
2. **Countries:** Which countries were most affected in 2026 compared with 2025?
3. **Iran:** How did the type of conflict in Iran change during 2026?
4. **Spillover:** Did the conflict spread to the Gulf states, and when?
5. **Lethality:** Which event types were the deadliest in 2026 compared with 2025?
""")
    with b:
        st.subheader("Data")
        st.markdown("""
**Source:** ACLED – Armed Conflict Location & Event Data, *Middle East aggregated data*
(weekly, by province), downloaded Nov 2026 from [acleddata.com](https://acleddata.com).

Each row is one **week × country × province × event type × sub-event type**, with the number
of **events** and reported **fatalities**.
""")
        st.dataframe(df[["WEEK", "COUNTRY", "ADMIN1", "EVENT_TYPE", "SUB_EVENT_TYPE", "EVENTS", "FATALITIES"]]
                     .sample(8, random_state=1).sort_values("WEEK"), hide_index=True, width="stretch",
                     column_config={"WEEK": st.column_config.DateColumn("WEEK", format="YYYY-MM-DD")})

# ---------- Q1 ----------
with tabs[1]:
    st.subheader("Q1 · When did the escalation start?")
    c1, c2 = st.columns([1, 3])
    with c1:
        sel = st.multiselect("Countries (empty = whole region)", ALL_COUNTRIES, key="q1c")
        metric = st.radio("Measure", ["EVENTS", "FATALITIES"], format_func=str.title, horizontal=True, key="q1m")
        log = st.toggle("Log scale", value=(metric == "FATALITIES"), key="q1log")
    d = cmp_ if not sel else cmp_[cmp_["COUNTRY"].isin(sel)]
    w = d.groupby(["YEAR", "WEEK_NO"])[metric].sum().unstack(0).reindex(range(1, N_WEEKS + 1)).fillna(0)
    fig = go.Figure()
    for yr, col in [(2025, C2025), (2026, C2026)]:
        if yr in w:
            fig.add_scatter(x=w.index, y=w[yr], name=str(yr), mode="lines", line=dict(color=col, width=3 if yr == 2026 else 2),
                            hovertemplate=f"{yr} · week %{{x}}<br>{metric.title()}: %{{y:,}}<extra></extra>")
    esc_wk = int(df.loc[df["WEEK"] == ESCALATION, "WEEK_NO"].iloc[0])
    fig.add_vline(x=esc_wk, line_dash="dash", line_color="#52514e",
                  annotation_text="28 Feb 2026", annotation_position="top right")
    fig.update_layout(xaxis_title="Week of the year", yaxis_title=metric.title(), hovermode="x unified")
    if log:
        fig.update_yaxes(type="log")
    with c2:
        st.plotly_chart(style(fig, 460), width="stretch")
    with c1:
        t = d.groupby("YEAR")[metric].sum()
        if 2025 in t and 2026 in t and t[2025] > 0:
            st.metric(f"{metric.title()} 2026 vs 2025", f"{t[2026]:,}", f"{t[2026] / t[2025] - 1:+.0%}")
    st.info("""
**Answer:** The region recorded **+26% events** and **+63% fatalities** compared with the same weeks of 2025
(the data ends in week 45 of 2026, so 2025 is limited to weeks 1–45 as well. Compared with *all* of 2025, 2026 still has **+12% events and +57% fatalities**).
The escalation started in the **week of 28 February 2026**. Events jumped from about 1,100 to more than 2,700 per week and peaked at 2,912 (week of 7 March).
A second rise started in **September–October 2026**. In the fatality curve, the **week of 3 January** stands out (about 27,700 deaths, mostly unrest in Iran),
which is 57% of all 2026 fatalities. Without it, 2026 had *fewer* recorded deaths than 2025.
""")

# ---------- Q2 ----------
with tabs[2]:
    st.subheader("Q2 · Which countries were most affected?")
    metric2 = st.radio("Measure", ["EVENTS", "FATALITIES"], format_func=str.title, horizontal=True, key="q2m")
    t = (cmp_[~cmp_["COUNTRY"].isin(SEAS)].groupby(["COUNTRY", "YEAR"])[metric2].sum()
         .unstack(fill_value=0).reindex(columns=[2025, 2026], fill_value=0))
    t = t.sort_values(2026)
    fig = go.Figure()
    for yr, col in [(2025, C2025), (2026, C2026)]:
        fig.add_bar(y=t.index, x=t[yr], name=str(yr), orientation="h", marker_color=col,
                    hovertemplate=f"%{{y}} · {yr}: %{{x:,}}<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05, xaxis_title=metric2.title())
    a, b = st.columns([3, 2])
    with a:
        st.plotly_chart(style(fig, 560), width="stretch")
    with b:
        tbl = (t.rename(columns={2025: "2025", 2026: "2026"}).sort_values("2026", ascending=False)
               .rename_axis("Country").reset_index())
        tbl["Difference"] = tbl["2026"] - tbl["2025"]          # absolute change: how much
        tbl["Change"] = (tbl["2026"] / tbl["2025"].replace(0, np.nan)).map(   # relative change: how fast
            lambda v: "new (0 in 2025)" if pd.isna(v) else f"×{v:.1f}")
        st.dataframe(tbl, width="stretch", height=560, hide_index=True, column_config={
            "Country": st.column_config.TextColumn("Country", width="medium"),
            "2025": st.column_config.NumberColumn("2025", format="localized"),
            "2026": st.column_config.NumberColumn("2026", format="localized"),
            "Difference": st.column_config.NumberColumn("Difference", format="localized",
                                                         help="2026 minus 2025 (absolute change)"),
            "Change": st.column_config.TextColumn("Change", help="2026 ÷ 2025 (relative change)"),
        })
    st.info("""
**Answer:** The centre of the conflict moved **from Gaza and Syria (2025) to Iran, Lebanon and Yemen (2026)**.
Lebanon had ×4.2 events, Iran ×2.8 events, and its fatalities rose from 1,293 to 29,695. Yemen had a similar number of events but ×4.4 fatalities.
Palestine still had the most events, but its fatalities fell from 16,453 to 1,709. The Gulf states went from almost zero to hundreds of events.
""")

# ---------- Q3 ----------
with tabs[3]:
    st.subheader("Q3 · How did the type of conflict change?")
    country3 = st.selectbox("Country", ALL_COUNTRIES, index=ALL_COUNTRIES.index("Iran"), key="q3c")
    metric3 = st.radio("Measure", ["EVENTS", "FATALITIES"], format_func=str.title, horizontal=True, key="q3m")
    p = (df[df["COUNTRY"] == country3].pivot_table(index="WEEK", columns="EVENT_TYPE", values=metric3,
                                                  aggfunc="sum", fill_value=0)
         .reindex(columns=TYPES, fill_value=0).reindex(sorted(df["WEEK"].unique()), fill_value=0))
    long = p.reset_index().melt(id_vars="WEEK", var_name="Event type", value_name=metric3.title())
    fig = px.area(long, x="WEEK", y=metric3.title(), color="Event type", color_discrete_map=TYPE_COLORS,
                  category_orders={"Event type": TYPES})
    fig.update_traces(line=dict(width=0.5), hovertemplate="%{x|%d %b %Y}<br>%{fullData.name}: %{y:,}<extra></extra>")
    fig.add_vline(x=ESCALATION, line_dash="dash", line_color="#52514e")
    fig.update_layout(xaxis_title=None, hovermode="x unified")
    st.plotly_chart(style(fig, 470), width="stretch")
    st.info("""
**Answer (Iran):** In 2025, Iran's events were mostly **protests**. 2026 had two phases:
**(1) January**, a protest and riot wave. In the week of 3 January ACLED records about 27,500 deaths, coded under *Riots* / *Protests (excessive force)*,
meaning they were most likely demonstrators killed during the suppression of the protests. **(2) From 28 February**, explosions and remote violence went from about 0 to **more than 500 events per week**
(3,596 in 2026 compared with 459 in 2025). So the conflict changed from **domestic unrest to an external military escalation**.
""")
    with st.expander("How does ACLED tell protests and riots apart?"):
        st.markdown("""
* **Protests:** the participants are *not* violent. Sub-types: *Peaceful protest*, *Protest with intervention*, and *Excessive force against protesters*
  (lethal force by authorities against peaceful demonstrators; this is the only protest sub-type that can involve deaths).
* **Riots:** the participants *themselves* are violent. Sub-types: *Violent demonstration* and *Mob violence*.
* The category describes how the **participants behaved**, not who caused the deaths.
""")

# ---------- Q4 ----------
with tabs[4]:
    st.subheader("Q4 · Did the conflict spread to the Gulf states?")
    c1, c2 = st.columns(2)
    countries4 = c1.multiselect("Countries", ALL_COUNTRIES, default=GULF, key="q4c")
    etype4 = c2.selectbox("Event type", TYPES, index=TYPES.index("Explosions/Remote violence"), key="q4t")
    months = pd.period_range("2025-01", df["WEEK"].max().to_period("M"), freq="M")
    g = df[df["COUNTRY"].isin(countries4) & (df["EVENT_TYPE"] == etype4)]
    heat = (g.pivot_table(index="COUNTRY", columns=g["WEEK"].dt.to_period("M"), values="EVENTS", aggfunc="sum", fill_value=0)
            .reindex(index=countries4, columns=months, fill_value=0))
    if countries4:
        fig = go.Figure(go.Heatmap(
            z=heat.values, x=[m.strftime("%b %Y") for m in months], y=heat.index, colorscale=SEQ_BLUE,
            xgap=2, ygap=2, text=np.where(heat.values > 0, heat.values, ""), texttemplate="%{text}",
            hovertemplate="%{y} · %{x}<br>Events: %{z}<extra></extra>", colorbar=dict(title="Events")))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(style(fig, 120 + 45 * len(countries4)), width="stretch")
    st.info("""
**Answer:** **Yes.** In 2025, the six Gulf states had only **6** explosion/remote-violence events. In 2026 they had **486**.
**All six recorded their first 2026 strike event in the same week, 28 February 2026.** The peak was in March (UAE 53, Kuwait 49).
After that, the UAE, Bahrain and Qatar calmed down, while **Saudi Arabia and Oman had a second wave in September–October**.
Fatalities stayed low, so this was mostly strike activity rather than heavy fighting.
""")

# ---------- Q5 ----------
with tabs[5]:
    st.subheader("Q5 · Which event types were the deadliest?")
    excl = st.toggle("Exclude Iran week of 3 Jan 2026 (outlier: ≈27,500 fatalities)", value=False, key="q5x")

    def leth(d):
        s = d.groupby("EVENT_TYPE")[["EVENTS", "FATALITIES"]].sum()
        return (s["FATALITIES"] / s["EVENTS"]).reindex(TYPES)

    d26 = cmp_[cmp_["YEAR"] == 2026]
    if excl:
        d26 = d26[~((d26["COUNTRY"] == "Iran") & (d26["WEEK"] == IRAN_JAN))]
    L = pd.DataFrame({"2025": leth(cmp_[cmp_["YEAR"] == 2025]), "2026": leth(d26)}).iloc[::-1]
    fig = go.Figure()
    for yr, col in [("2025", C2025), ("2026", C2026)]:
        fig.add_bar(y=L.index, x=L[yr], name=yr, orientation="h", marker_color=col,
                    text=L[yr].map("{:.2f}".format), textposition="outside",
                    hovertemplate=f"%{{y}} · {yr}: %{{x:.2f}} fatalities / event<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.25, xaxis_title="Reported fatalities per event")
    st.plotly_chart(style(fig, 470), width="stretch")
    st.info("""
**Answer:** In 2025 the deadliest types were *Explosions/Remote violence* (1.32), *Battles* (1.28) and *Violence against civilians* (1.08).
In 2026, *Riots* look deadliest (3.28), but **switch on the toggle**: this comes entirely from one Iranian week. Without it, **Battles (2.20) are the deadliest**.
Strikes became much more frequent (24,527 vs 13,653 events) but **less deadly per event** (0.41 vs 1.32).
The lesson: always check whether a summary statistic depends on a single outlier.
""")

# ---------- Map ----------
with tabs[6]:
    st.subheader("Where did it happen?")
    c1, c2 = st.columns(2)
    yr_m = c1.radio("Year", [2025, 2026], index=1, horizontal=True, key="mapy")
    size_by = c2.radio("Bubble size", ["FATALITIES", "EVENTS"], format_func=str.title, horizontal=True, key="maps")
    prov = (df[(df["YEAR"] == yr_m) & ~df["COUNTRY"].isin(SEAS)].groupby(["COUNTRY", "ADMIN1"])
            .agg(EVENTS=("EVENTS", "sum"), FATALITIES=("FATALITIES", "sum"),
                 lat=("CENTROID_LATITUDE", "first"), lon=("CENTROID_LONGITUDE", "first")).reset_index())
    prov = prov[prov[size_by] > 0]
    fig = px.scatter_geo(prov, lat="lat", lon="lon", size=size_by, size_max=45, color_discrete_sequence=[C2026],
                         hover_name="ADMIN1", hover_data={"COUNTRY": True, "EVENTS": ":,", "FATALITIES": ":,",
                                                         "lat": False, "lon": False})
    fig.update_traces(marker=dict(opacity=0.6, line=dict(width=1, color="white")))
    fig.update_geos(projection_type="mercator", lataxis_range=[11, 43], lonaxis_range=[25, 63],
                    showcountries=True, countrycolor="#c9c8c2", showland=True, landcolor="#f6f5f1",
                    showocean=True, oceancolor="#eaf1f8", showframe=False)
    st.plotly_chart(style(fig, 760), width="stretch")
    st.caption("Bubble area ∝ total per province (ADMIN1) for the selected year. Hover a bubble for details.")

# ---------- Conclusion ----------
with tabs[7]:
    st.subheader("Conclusion")
    st.markdown("""
* **2026 was a year of escalation:** +26% events and +63% reported fatalities compared with the same weeks of 2025
  (and still +12% / +57% compared with the *whole* of 2025, even though 2026 has 7 fewer weeks of data).
* **Two stages:** a deadly **wave of unrest in Iran in January**, then from **28 February 2026** a **regional strike campaign**
  that more than doubled weekly events and reached **all six Gulf states in the same week**.
* **The centre of the conflict moved** from Gaza and Syria to **Iran, Lebanon and Yemen**.
* **One outlier week** has a strong effect on the 2026 fatality figures. Without it, 2026 had more events than 2025 but fewer deaths.

**Limitations:** ACLED counts *reported* events (media access matters, especially in Iran and Yemen); fatalities are estimates;
protest/riot coding depends on how sources describe events; the aggregated data has no actor information.
""")
    st.caption("Data: ACLED, www.acleddata.com · Raleigh, Linke, Hegre & Karlsen (2010), Journal of Peace Research 47(5).")
