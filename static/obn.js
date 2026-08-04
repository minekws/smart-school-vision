export function obnaruz(Data, containerId = 'wrapper') {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Контейнер #${containerId} не найден`);
        return;
    }

    container.innerHTML = '';
    container.style.display = 'flex';
    container.style.justifyContent = 'center';
    container.style.width = '100%';

    const table = document.createElement('table');
    table.style.width = '100%';
    table.style.maxWidth = '800px';
    table.style.borderCollapse = 'collapse';
    table.style.fontFamily = 'Nunito';
    table.style.margin = '20px 0';

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');

    ['ID', 'ФИО', 'Опоздание', 'Камера', 'Время'].forEach(text => {
        const th = document.createElement('th');
        th.textContent = text;
        th.style.padding = '12px 8px';
        th.style.textAlign = 'center';
        th.style.fontSize = '16px';
        th.style.fontWeight = '600';
        th.style.fontFamily = 'Nunito';
        th.style.borderBottom = '2px solid #f0f0f0';
        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');

    Data.obnaruz.forEach(item => {
        const row = document.createElement('tr');
        row.style.borderBottom = '1px solid #f0f0f0';

        const idCell = document.createElement('td');
        idCell.textContent = item.id;
        idCell.style.padding = '12px 8px';
        idCell.style.fontSize = '16px';
        idCell.style.textAlign = 'center';
        row.appendChild(idCell);

        const nameCell = document.createElement('td');
        nameCell.style.padding = '12px 8px';
        nameCell.style.fontSize = '16px';
        nameCell.style.textAlign = 'center';
        nameCell.style.display = 'flex';
        nameCell.style.alignItems = 'center';
        nameCell.style.justifyContent = 'center';
        nameCell.style.gap = '8px';

        const randomIconNum = Math.floor(Math.random() * 8) + 1;
        const icon = document.createElement('div');
        icon.className = `ic${randomIconNum}`;
        icon.style.height = '24px';
        icon.style.width = '24px';
        icon.style.display = 'flex';
        icon.style.alignItems = 'center';
        icon.style.justifyContent = 'center';
        icon.innerHTML = `<img src="static/ima/ic${randomIconNum}.svg" width="24" height="24">`;

        nameCell.appendChild(icon);
        nameCell.appendChild(document.createTextNode(item.name));
        row.appendChild(nameCell);

        const opozCell = document.createElement('td');
        opozCell.textContent = item.opoz;
        opozCell.style.padding = '6px 12px';
        opozCell.style.fontWeight = '500';
        opozCell.style.borderRadius = '6px';
        opozCell.style.display = 'inline-block';
        opozCell.style.margin = '0 auto';

        if (item.opoz === 'Да') {
            opozCell.style.color = '#d32f2f';
            opozCell.style.backgroundColor = '#ffebee';
        } else {
            opozCell.style.color = '#388e3c';
            opozCell.style.backgroundColor = '#e8f5e9';
        }

        const opozWrapper = document.createElement('td');
        opozWrapper.style.padding = '12px 8px';
        opozWrapper.style.textAlign = 'center';
        opozWrapper.appendChild(opozCell);
        row.appendChild(opozWrapper);

        const Camera = document.createElement('td');
        Camera.textContent = item.camera;
        Camera.style.padding = '12px 8px';
        Camera.style.fontSize = '16px';
        Camera.style.textAlign = 'center';
        row.appendChild(Camera);

        const timeCell = document.createElement('td');
        timeCell.textContent = item.time;
        timeCell.style.padding = '12px 8px';
        timeCell.style.fontSize = '16px';
        timeCell.style.textAlign = 'center';
        row.appendChild(timeCell);

        tbody.appendChild(row);
    });

    table.appendChild(tbody);
    container.appendChild(table);
}