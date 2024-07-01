import locale

import altair as alt
import pandas as pd
import streamlit as st
import robin_stocks.robinhood as rs


def format_currency(value):
    locale.setlocale(locale.LC_ALL, 'EN_US')
    return locale.currency(value, grouping=True)


def format_percent(value, basis):
    return f"{value / basis:.2%}"


def load_account():
    account = rs.build_user_profile()
    account['cash'] = float(account['cash'])
    return account


def load_holdings():
    raw_holdings = rs.build_holdings()
    holdings = []

    for k in raw_holdings:
        s = raw_holdings[k].copy()
        s['symbol'] = k
        holdings.append(s)

    leverage = pd.read_csv('leverage.csv')
    holdings = pd.DataFrame(holdings)

    for c in holdings.columns:
        try:
            values = holdings[c].astype(float)
        except ValueError:
            values = holdings[c]
        finally:
            holdings[c] = values

    holdings = holdings.merge(leverage, how='left', on='symbol')
    holdings['leverage'] = holdings['leverage'].fillna(1)
    holdings['exposure'] = holdings['equity'] * holdings['leverage']
    holdings['exposure_change'] = holdings['equity_change'] * holdings['leverage']
    holdings['previous_exposure'] = holdings['exposure'] - holdings['exposure_change']

    return holdings


def login_page():
    st.title('Login')
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    enter = st.button('Login', type='primary')
    if enter:
        try:
            rs.login(username, password, store_session=False)
            st.session_state['login'] = True
        except Exception as e:
            st.error(e, icon='⚠')


def display_exposures(account, holdings):
    equity = holdings['equity'].sum()
    equity_change = holdings['equity_change'].sum()

    cash = account['cash']
    cash_change = cash

    assets = equity + cash

    gross_exposure = holdings['exposure'].abs().sum()
    gross_exposure_change = gross_exposure - holdings['previous_exposure'].abs().sum()

    net_exposure = holdings['exposure'].sum()
    net_exposure_change = net_exposure - holdings['previous_exposure'].sum()

    long_side = holdings['exposure'] > 0
    long_exposure = holdings.loc[long_side, 'exposure'].sum()
    long_exposure_change = long_exposure - holdings.loc[long_side, 'previous_exposure'].sum()

    short_side = holdings['exposure'] < 0
    short_exposure = holdings.loc[short_side, 'exposure'].sum()
    short_exposure_change = short_exposure - holdings.loc[short_side, 'previous_exposure'].sum()

    percent_view = st.toggle('Percentage View', value=True)
    dollar_columns = st.columns(3)
    exposure_columns = st.columns(3)
    st.write('######')
    display_holdings = holdings[['symbol', 'exposure']].copy()

    if percent_view:
        exposure_display = lambda v: format_percent(v, assets)
        display_holdings['exposure'] /= assets
        exposure_axis = alt.Axis(format='%')
    else:
        exposure_display = lambda v: format_currency(v)
        exposure_axis = alt.Axis(format='$,f')

    dollar_columns[0].metric('Assets', f"{format_currency(assets)}", f"{exposure_display(equity_change)}")
    dollar_columns[1].metric('Equity', f"{exposure_display(equity)}", f"{exposure_display(equity_change)}")
    dollar_columns[2].metric('Cash', f"{exposure_display(cash)}", f"{exposure_display(cash_change)}")

    exposure_columns[0].metric('Gross Exposure', f"{exposure_display(gross_exposure)}", f"{exposure_display(gross_exposure_change)}")
    exposure_columns[1].metric('Long Exposure', f"{exposure_display(long_exposure)}", f"{exposure_display(long_exposure_change)}")
    exposure_columns[2].metric('Short Exposure', f"{exposure_display(-short_exposure)}", f"{exposure_display(-short_exposure_change)}")

    chart = alt.Chart(display_holdings).mark_bar().encode(
        x=alt.X('symbol:N', sort='y', title='Symbol'),
        y=alt.Y('exposure:Q', title='Exposure', axis=exposure_axis),
        color=alt.condition(
            alt.datum.exposure > 0,
            alt.value('#91e879'),
            alt.value('#ff475d')
        )
    )
    st.altair_chart(chart, use_container_width=True)


def main():
    st.set_page_config('Portfolio', layout='wide')

    if 'login' in st.session_state and st.session_state['login']:
        st.title('Portfolio')
        account = load_account()
        holdings = load_holdings()
        display_exposures(account, holdings)
    else:
        login_page()


if __name__ == '__main__':
    main()
