#!/usr/bin/env python3
"""Exact two-date rebalancing, finite stopping and cash ledgers. Synthetic, not a market fit."""
import argparse
from fractions import Fraction as F
from itertools import product
import json
from pathlib import Path
from html import escape


NODES = ['', 'U', 'D', 'UU', 'UD', 'DU', 'DD']
LEAVES = ['UU', 'UD', 'DU', 'DD']


def trade(su, sd, fu, fd, r):
    delta = (fu-fd)/(su-sd)
    cash = (su*fd-sd*fu)/(r*(su-sd))
    assert delta*su+r*cash == fu and delta*sd+r*cash == fd
    return delta, cash


def rules():
    # Root stopping ends the rule; unreachable later choices are not distinct stopping times.
    return [('stop', None, None)] + [('wait', u, d) for u, d in product(['stop', 'wait'], repeat=2)]


def tau(rule, path):
    if rule[0] == 'stop': return 0
    return 1 if rule[1 if path[0] == 'U' else 2] == 'stop' else 2


def economy(spot, up, down, r, strike, ps):
    if not (spot > 0 and up > down > 0 and down < r < up and strike >= 0):
        raise ValueError('require positive spot, 0 < down < R < up, and nonnegative strike')
    if not ps or any(not 0 < p < 1 for p in ps):
        raise ValueError('each physical conditional up probability must be strictly between 0 and 1')
    q = (r-down)/(up-down)
    s = {n: spot * up**n.count('U') * down**n.count('D') for n in NODES}
    b = {n: r**len(n) for n in NODES}
    g = {n: max(strike-s[n], F(0)) for n in NODES}
    qpath = {n: q**n.count('U')*(1-q)**n.count('D') for n in LEAVES}
    euro = {n: g[n] for n in LEAVES}
    amer = dict(euro)
    continuation = {}
    euro_trades = {}
    for n in ['U', 'D', '']:
        euro[n] = (q*euro[n+'U']+(1-q)*euro[n+'D'])/r
        continuation[n] = (q*amer[n+'U']+(1-q)*amer[n+'D'])/r
        amer[n] = max(g[n], continuation[n])
        delta, cash = trade(s[n+'U'], s[n+'D'], euro[n+'U'], euro[n+'D'], r)
        assert delta*s[n]+cash == euro[n]
        euro_trades[n or 'root'] = dict(delta=delta, cash_value=cash, bank_units=cash/b[n],
                                      current_wealth=euro[n], child_wealth=[delta*s[n+c]+r*cash for c in 'UD'])
    # Strictly self-financing seller: retain every continuation surplus in the bank.
    wealth = {'': amer['']}
    seller = {}
    for n in ['', 'U', 'D']:
        delta, base_cash = trade(s[n+'U'], s[n+'D'], amer[n+'U'], amer[n+'D'], r)
        surplus = wealth[n]-continuation[n]
        assert surplus >= 0 and delta*s[n]+base_cash == continuation[n]
        cash = base_cash+surplus
        assert delta*s[n]+cash == wealth[n]
        for c in 'UD':
            wealth[n+c] = delta*s[n+c]+r*cash
            assert wealth[n+c] == amer[n+c]+r*surplus and wealth[n+c] >= g[n+c]
        seller[n or 'root'] = dict(delta=delta, cash_value=cash, bank_units=cash/b[n],
                                  wealth=wealth[n], snell_value=amer[n], continuation_cost=continuation[n],
                                  retained_cash=surplus, child_wealth=[wealth[n+c] for c in 'UD'])
    policies = []
    for rule in rules():
        stops = {path: tau(rule, path) for path in LEAVES}
        payments = {path: g[path[:stops[path]]] for path in LEAVES}
        discounted = {path: payments[path]/r**stops[path] for path in LEAVES}
        expectation = sum((qpath[path]*discounted[path] for path in LEAVES), F(0))
        seller_surplus = {path: wealth[path[:stops[path]]]-payments[path] for path in LEAVES}
        assert all(x >= 0 for x in seller_surplus.values())
        policies.append(dict(rule=list(rule), stopping_dates=stops, payments=payments,
                             discounted_payments=discounted, value0=expectation, seller_surplus=seller_surplus))
    best = max(p['value0'] for p in policies)
    assert best == amer[''] and euro[''] == policies[-1]['value0']
    optimal_dates = {}
    for path in LEAVES:
        optimal_dates[path] = next(t for t in range(3) if g[path[:t]] == amer[path[:t]])
        assert wealth[path[:optimal_dates[path]]] == g[path[:optimal_dates[path]]]
    prophet_discounted = {}
    prophet_dates = {}
    for path in LEAVES:
        options = [g[path[:t]]/r**t for t in range(3)]
        prophet_discounted[path] = max(options)
        prophet_dates[path] = options.index(max(options))
    prophet = sum((qpath[path]*prophet_discounted[path] for path in LEAVES), F(0))
    assert max(g[''], euro['']) <= amer[''] <= prophet
    # P-Q-m representations: changing P preserves priced quantities, changes the density.
    densities = []
    for p in ps:
        mu, md = q/(r*p), (1-q)/(r*(1-p))
        assert p*mu+(1-p)*md == 1/r
        assert p*mu*up*spot+(1-p)*md*down*spot == spot
        ppath = {n: p**n.count('U')*(1-p)**n.count('D') for n in LEAVES}
        cumulative = {n: (mu**n.count('U')*md**n.count('D')) for n in LEAVES}
        assert all(cumulative[n] == qpath[n]/(ppath[n]*r**2) for n in LEAVES)
        epmx = sum((ppath[n]*cumulative[n]*g[n] for n in LEAVES), F(0))
        assert epmx == euro['']
        densities.append(dict(P_up=p, step_m=[mu, md], cumulative_m=cumulative, euro_via_P=epmx))
    # A static stock/bank line fitting two distinct terminal stock values fails at the third.
    static_delta = (g['UU']-g['UD'])/(s['UU']-s['UD'])
    terminal_cash = g['UU']-static_delta*s['UU']
    static_prediction = static_delta*s['DD']+terminal_cash
    nodes = {n or 'root': dict(S=s[n], B=b[n], exercise=g[n], euro=euro[n], amer=amer[n],
                              continuation=continuation.get(n)) for n in NODES}
    return dict(parameters=dict(spot=spot, up=up, down=down, R=r, strike=strike), Q_up=q, local_state_prices=[q/r, (1-q)/r], Q_leaves=qpath, nodes=nodes,
                euro_trades=euro_trades, seller_trades=seller,
                seller_terminal_wealth={n: wealth[n] for n in LEAVES},
                policies=policies, optimal_dates=optimal_dates, euro0=euro[''], amer0=amer[''],
                early_exercise_premium=amer['']-euro[''], prophet0=prophet,
                prophet_dates=prophet_dates, prophet_discounted=prophet_discounted,
                densities=densities, static_fit=dict(delta=static_delta, terminal_cash=terminal_cash,
                predicted_DD=static_prediction, required_DD=g['DD'], replicated=static_prediction==g['DD']))


def as_json(value):
    if isinstance(value, F): return str(value)
    if isinstance(value, dict): return {k: as_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [as_json(v) for v in value]
    return value


def figure(result):
    base = result['baseline']
    r, q, strike = base['parameters']['R'], base['Q_up'], base['parameters']['strike']
    positions = {'root': (100, 220), 'U': (430, 120), 'D': (430, 340),
                 'UU': (800, 60), 'UD': (800, 180), 'DU': (800, 300), 'DD': (800, 420)}
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="950" viewBox="0 0 1100 950">',
           '<title>两期put：条件定价、合法行权和先知上界</title>',
           '<desc>完整历史树每节点列股票价S、欧式E、美式V、当日行权g；按结果高亮到达且合同尚存时应行权的节点。下方五种合法停止值与逐路径最大上界统一为零日货币。</desc>',
           '<rect width="1100" height="950" fill="white"/>',
           '<style>text{font-family:"Arial","PingFang SC",sans-serif;fill:#182536;font-size:17px}.small{font-size:15px}.title{font-size:25px;font-weight:bold}.box{fill:#f2f7fc;stroke:#476887;stroke-width:1.5}.stop{fill:#fff1d6;stroke:#915b05;stroke-width:2.5}</style>',
           '<text class="title" x="35" y="32">Two-step put: rebalance and exercise with current information</text>',
           f'<text class="small" x="35" y="57">Synthetic; nodes: local-date money; bars: date-0 money; K={strike}, R={r}, Q(up)={q}</text>']
    for parent, children in [('root', ['U', 'D']), ('U', ['UU', 'UD']), ('D', ['DU', 'DD'])]:
        x, y = positions[parent]
        for child in children:
            xx, yy = positions[child]
            svg.append(f'<line x1="{x+160}" y1="{y+32}" x2="{xx}" y2="{yy+32}" stroke="#7f91a1" stroke-width="2"/>')
    for name, (x, y) in positions.items():
        node = base['nodes'][name]
        exercise_now = name in ['root', 'U', 'D'] and node['exercise'] >= node['continuation']
        css = 'stop' if exercise_now else 'box'
        svg.append(f'<rect class="{css}" x="{x}" y="{y}" width="185" height="85" rx="8"/>')
        title = '0' if name == 'root' else name
        svg.append(f'<text x="{x+10}" y="{y+23}">{title} · S={node["S"]}</text>')
        svg.append(f'<text class="small" x="{x+10}" y="{y+48}">E={node["euro"]} · V={node["amer"]}</text>')
        svg.append(f'<text class="small" x="{x+10}" y="{y+71}">g={node["exercise"]}'+(' * stop if reached' if exercise_now else '')+'</text>')
    svg += [f'<text class="small" x="35" y="545">UD and DU both end at {base["nodes"]["UD"]["S"]}; their histories and prior exercise decisions differ.</text>',
            '<text x="35" y="585">Five legal stopping rules and a pathwise upper bound (date-0 money)</text>']
    vals = [p['value0'] for p in base['policies']]+[base['prophet0']]
    labels = ['root: stop', 'U: stop / D: stop', 'U: stop / D: wait', 'U: wait / D: stop', 'U: wait / D: wait', 'pathwise-max bound']
    maxval = max(float(v) for v in vals)
    for i, (value, label) in enumerate(zip(vals, labels)):
        y = 615+i*44
        length = 500*float(value)/(maxval or 1)
        is_best = i < 5 and value == base['amer0']
        fill = '#915b05' if is_best else ('#a23b52' if i == 5 else '#406f99')
        if is_best: label += ' *'
        svg.append(f'<text class="small" x="35" y="{y+19}">{escape(label)}</text>')
        svg.append(f'<rect x="235" y="{y}" width="{length:.4f}" height="25" fill="{fill}"/>')
        svg.append(f'<text class="small" x="{250+length:.4f}" y="{y+19}">{value} ≈ {float(value):.5f}</text>')
    svg += ['<text class="small" x="35" y="916">* Highlighted legal maximizers = Snell root; red: pathwise-max bound, not a new admissible action.</text>', '</svg>']
    return '\n'.join(svg)+'\n'


def run(data):
    if data['periods'] != 2: raise ValueError('this finite audit enumerates exactly two periods')
    spot, up, down, r = [F(data[k]) for k in ['spot', 'up', 'down', 'gross_bank_return']]
    k, km = F(data['strike']), F(data['migration_strike'])
    ps = [F(p) for p in data['physical_up_probabilities']]
    fee = F(data['mandatory_time1_fee'])
    endpoint = F(data['endpoint_D_gross_return'])
    if fee < 0: raise ValueError('mandatory fee must be nonnegative')
    if endpoint != up: raise ValueError('declared endpoint witness requires R_D = up')
    baseline = economy(spot, up, down, r, k, ps)
    migration = economy(spot, up, down, r, km, ps)
    endpoint_payoffs = [endpoint*spot*down-spot*down*move for move in [up, down]]
    assert endpoint_payoffs[0] == 0 and endpoint_payoffs[1] > 0
    return dict(identity=data['identity'], baseline=baseline, migration=migration,
                mandatory_fee=dict(time1=fee, extra_initial_bank_cash=fee/r, reserve_at1=(fee/r)*r),
                illegal_future_position=dict(delta_up=1, delta_down=-1, is_predictable=False,
                    claimed_gains=[spot*(up-r), spot*(r-down)]),
                endpoint_D=dict(stock_units=-1, current_bank_cash=spot*down, R_D=endpoint,
                    initial_cost0=0, trade_only_after_history='D', terminal_payoffs={'UU': F(0), 'UD': F(0),
                    'DU': endpoint_payoffs[0], 'DD': endpoint_payoffs[1]}, Q_up=F(1), equivalent_to_P=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(json.loads(args.inputs.read_text(encoding='utf-8')))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'exact-results.json').write_text(json.dumps(as_json(result), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (args.out/'dynamic-tree.svg').write_text(figure(result), encoding='utf-8')
    print('PASS exact recursion, five legal stopping rules, every-node rebalancing, all-rule seller cover, P-Q-m and declared boundary witnesses')
    print('baseline euro0='+str(result['baseline']['euro0'])+' amer0='+str(result['baseline']['amer0'])+' prophet0='+str(result['baseline']['prophet0']))
    print('migration euro0='+str(result['migration']['euro0'])+' amer0='+str(result['migration']['amer0']))


if __name__ == '__main__':
    main()
