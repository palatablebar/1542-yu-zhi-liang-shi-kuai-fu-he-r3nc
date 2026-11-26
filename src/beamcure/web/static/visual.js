function renderVisual(target, data) {
    const sets = [
        ['压机复压与暂停', data.rows.filter(row => ['已分派','暂停','候补'].includes(row.state))],
        ['常规观察与判读', data.rows.filter(row => ['人工判读','观察'].includes(row.state))]
    ];
    const cards = node('div',undefined,'pairs');
    for (const [title, rows] of sets) {
        const card = node('section',undefined,'proof-side');
        card.append(node('h3',`${title} · ${rows.length} 批`));
        if (!rows.length) card.append(node('p','本班无记录'));
        for (const row of rows.slice(0,5)) {
            const line = node('div',undefined,'strength-line');
            const percent = `${Math.round(row.estimate * 100)}%`;
            const gauge = node('meter');
            gauge.min = 0;
            gauge.max = 1;
            gauge.value = row.estimate;
            gauge.setAttribute('aria-label',`${row.key} 强度风险 ${percent}`);
            const ticket = node('button',row.key,'item-link');
            ticket.addEventListener('click',() => inspect(row));
            line.append(ticket,gauge,node('span',percent));
            card.append(line);
        }
        cards.append(card);
    }
    target.append(cards);
}
