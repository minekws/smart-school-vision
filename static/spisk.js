document.addEventListener('DOMContentLoaded', () => {

    const notificationContainer = document.getElementById('notification-container');
    let notificationTimer = null;
    let userActivityChart = null;
    let userListData = [];
    let userInfoData = [];

    function showNotification(message, type = 'success') {

        clearTimeout(notificationTimer);

        notificationContainer.textContent = message;
        notificationContainer.classList.remove('notification-success', 'notification-error');
        notificationContainer.classList.add(type === 'success' ? 'notification-success' : 'notification-error');
        notificationContainer.classList.add('show');

        notificationTimer = setTimeout(() => {
            notificationContainer.classList.remove('show');
        }, 4000);
    }

    const name = document.getElementById('user-name');
    const role = document.getElementById('user-role');
    const updateUI = () => {
        name.innerHTML = localStorage.getItem('username');
        role.innerHTML = localStorage.getItem('userRole');
    }
    const timeToMinutes = (timeStr) => {
        if (!timeStr || !timeStr.includes(':')) return 0;
        const [hours, minutes] = timeStr.split(':').map(Number);
        return hours * 60 + minutes;
    };

    const minutesToTime = (totalMinutes) => {
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
    };
    window.sortTable = sortTable;
    window.toggleDropdown = toggleDropdown;

    document.getElementById('addBtn').onclick = function() {
        document.getElementById('addCustomerModal').classList.add('open');
    };
    document.getElementById('closeAddCustomer').onclick = function() {
        document.getElementById('addCustomerModal').classList.remove('open');
    };

    document.getElementById('addCustomerModal').addEventListener('click', function(e) {
        if (e.target === this) this.classList.remove('open');
    });

    let editIndex = null;
    let itemToDelete = null;

    const avatarInput = document.getElementById('avatarInput');
    const avatarPreview = document.getElementById('avatarPreview');

    avatarInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                avatarPreview.innerHTML = `<img src="${e.target.result}" alt="Avatar">`;
            }
            reader.readAsDataURL(this.files[0]);
        } else {
            avatarPreview.innerHTML = `<span class="camera-icon">&#128247;</span>`;
        }
    });

    function mergeAndRenderData() {

        const formattedCustomers = userListData.map(baseUser => {

            const detailedInfo = userInfoData.find(info => info.id === baseUser.id);

            return {
                ...baseUser,
                ...detailedInfo
            };
        });

        customers.length = 0;
        customers.push(...formattedCustomers);
        renderTable(customers);
        console.log("Данные успешно объединены и таблица отрисована.", customers);
    }

    function selectRow(event) {
        if (event.target.closest('.actions')) {
            return;
        }

        const clickedRow = event.target.closest('tr');
        if (!clickedRow) return;

        document.querySelectorAll('#customerTable tbody tr.active').forEach(row => {
            row.classList.remove('active');
        });

        clickedRow.classList.add('active');

        const index = Array.from(clickedRow.parentNode.children).indexOf(clickedRow);
        if (index >= 0 && customers[index]) {
            displayUserInfo(customers[index]);
        }
    }

    function displayUserInfo(user) {

        console.log(user);
        const avatarImg = document.getElementById('userAvatarInfo');
        if (user.avatar && user.avatar !== 'static/ima/ic3.svg') {
            avatarImg.src = user.avatar;
        } else {
            avatarImg.src = 'static/ima/ic3.svg';
        }
        document.getElementById('userNameInfo').textContent = user.name || 'Не указано';
        document.getElementById('userRoleInfo').textContent = user.accon || '—';
        document.getElementById('userEmailInfo').textContent = user.email || 'Не указан';

        let lastDetectedText = 'Нет данных';
        if (user.last_detected) {
            const date = new Date(user.last_detected);
            lastDetectedText = `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
        }
        document.getElementById('lastDetectedInfo').textContent = lastDetectedText;

        const detections = user.detections_last_7_days || {};
        const detectedDates = Object.keys(detections).sort();

        const chartData = {
            categories: [],
            seriesData: []
        };

        const timeValuesInMinutes = [];

        for (const date of detectedDates) {
            chartData.categories.push(date);

            const detectionTime = detections[date];
            if (detectionTime) {
                const minutes = timeToMinutes(detectionTime);
                chartData.seriesData.push(minutes);
                timeValuesInMinutes.push(minutes);
            } else {
                chartData.seriesData.push(0);
            }
        }

        let yAxisMin = timeToMinutes('07:30');
        let yAxisMax = timeToMinutes('09:00');

        if (timeValuesInMinutes.length > 0) {

            const minTime = Math.min(...timeValuesInMinutes);
            const maxTime = Math.max(...timeValuesInMinutes);

            yAxisMin = Math.floor((minTime - 15) / 5) * 5;
            yAxisMax = Math.ceil((maxTime + 15) / 5) * 5;

            if (yAxisMin < 0) yAxisMin = 0;
        }


        const chartOptions = {
            series: [{
                name: 'Время обнаружения',
                data: chartData.seriesData
            }],
            chart: {
                type: 'bar',
                height: 250,
                toolbar: { show: false },
                fontFamily: 'Nunito, sans-serif'
            },
            plotOptions: {},
            dataLabels: {
                enabled: false
            },
            legend: {},
            xaxis: {
                categories: chartData.categories,
                labels: {
                    style: { fontSize: '12px' }
                }
            },

            yaxis: {
                min: yAxisMin,
                max: yAxisMax,
                tickAmount: 6,
                labels: {
                    formatter: (value) => {

                        const roundedValue = Math.round(value);
                        if (roundedValue <= 0) return '';
                        return minutesToTime(roundedValue);
                    }
                }
            },
            tooltip: {},
            noData: {
                text: 'Нет данных об активности'
            }
        };

        if (!userActivityChart) {
            userActivityChart = new ApexCharts(document.querySelector("#activityChart"), chartOptions);
            userActivityChart.render();
        } else {
            userActivityChart.updateOptions(chartOptions, true);
        }
    }

    window.selectRow = selectRow;

    const customers = [];

    let sortDirection = [true, true, true, true];

    function renderTable(data) {
        const tbody = document.querySelector("#customerTable tbody");
        tbody.innerHTML = "";
        data.forEach((c, idx) => {

            tbody.innerHTML += `
          <tr onclick="selectRow(event)">
            <td class="id-cell">
                <span class="id">${c.id}</span>
            </td>
            <td class="name-cell">
              <img class="avatar" src="${c.avatar}" onerror="this.onerror=null; this.src='static/ima/ic3.svg';" alt="avatar">
              ${c.name}
            </td>
            <td>${c.email}</td>
            <td>
              <span class="accon ${c.accon.toLowerCase()}">${c.accon}</span>
            </td>
            <td class="actions">
              <button class="dots" onclick="toggleDropdown(event, ${idx})">&#8942;</button>
              <div class="dropdown" id="dropdown-${idx}">
                <button onclick="editCustomer(${idx})">Edit</button>
                <button class="delete" onclick="confirmDelete(${idx})">Delete</button>
              </div>
            </td>
          </tr>
        `;
        });
    }
    window.renderTable = renderTable;

    function sortTable(col) {
        customers.sort((a, b) => {
            let valA, valB;
            switch (col) {
                case 0:
                    valA = a.id;
                    valB = b.id;
                    break;
                case 1:
                    valA = a.name;
                    valB = b.name;
                    break;
                case 2:
                    valA = a.email;
                    valB = b.email;
                    break;
                case 3:
                    valA = a.accon;
                    valB = b.accon;
                    break;
            }
            if (valA < valB) return sortDirection[col] ? -1 : 1;
            if (valA > valB) return sortDirection[col] ? 1 : -1;
            return 0;
        });
        sortDirection[col] = !sortDirection[col];
        renderTable(customers);
    }

    function toggleDropdown(e, idx) {
        e.stopPropagation();

        const currentDropdown = document.getElementById('dropdown-' + idx);
        const parentRow = currentDropdown.closest('tr');
        const wasOpen = currentDropdown.classList.contains('show');

        document.querySelectorAll('.dropdown.show').forEach(d => {
            d.classList.remove('show');
        });
        document.querySelectorAll('tbody tr.row-dropdown-open').forEach(row => {
            row.classList.remove('row-dropdown-open');
        });

        if (!wasOpen) {
            currentDropdown.classList.add('show');
            if (parentRow) {
                parentRow.classList.add('row-dropdown-open');
            }
        }
    }

    document.addEventListener('click', () => {

        document.querySelectorAll('.dropdown.show').forEach(d => {
            d.classList.remove('show');
        });

        document.querySelectorAll('tbody tr.row-dropdown-open').forEach(row => {
            row.classList.remove('row-dropdown-open');
        });
    });
    let avatarDataUrl = "";

    avatarInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                avatarDataUrl = e.target.result;
                avatarPreview.innerHTML = `<img src="${avatarDataUrl}" alt="Avatar">`;
            }
            reader.readAsDataURL(this.files[0]);
        } else {
            avatarDataUrl = "";
            avatarPreview.innerHTML = `<span class="camera-icon">&#128247;</span>`;
        }
    });

    document.getElementById('addCustomerForm').addEventListener('submit', async function(e) {
        e.preventDefault();

        const firstName = this.firstName.value.trim();
        const lastName = this.lastName.value.trim();
        const email = this.email.value.trim();
        const accon = this.accon.value;
        const password = this.password.value;
        const id = this.id.value;

        const avatar = avatarDataUrl;

        if (!firstName || !lastName || !email) {
            showNotification('Пожалуйста, заполните все поля.');
            return;
        }
        if (password.length < 6) {
            showNotification('Пароль должен содержать не менее 6 символов');
            return;
        }
        if (!avatar) {
            showNotification("Пожалуйста, загрузите фото.");
            return;
        }
        const cameraId = localStorage.getItem('cameraId');
        if (!cameraId) {
            showNotification("Ошибка: ID камеры не найден. Невозможно добавить пользователя.");
            return;
        }

        const userData = {
            role: accon === 'Админ' ? 'moderator' : 'user',
            userName: `${firstName} ${lastName}`,
            email: email,
            password: password,
            camera_id: cameraId,
            photo: avatar.includes(',') ? avatar.split(',')[1] : avatar
        };

        if (editIndex !== null) {

            const editdata = {
                sub_action: 'edit',
                id: customers[editIndex].id,
                role: accon === 'Админ' ? 'moderator' : 'user',
                username: `${firstName} ${lastName}`,
                mail: email,
                password: password,
                camera_id: localStorage.getItem('cameraId'),
                photo: avatar.includes(',') ? avatar.split(',')[1] : avatar
            };
            const response = await wsClient.sendWithResponse('manage_account', editdata);
            console.log("Сервер ответил:", response);

            if (response.success) {

                showNotification("Изменения приняты в силу");

                customers[editIndex] = {
                    id: customers[editIndex].id,
                    name: userData.userName,
                    email: userData.email,
                    accon: accon,
                    avatar: avatar
                };

                renderTable(customers);
                editIndex = null;
            }
        } else {

            try {
                console.log("Отправка данных нового пользователя на сервер:", userData);

                const response = await wsClient.sendWithResponse('register', userData);

                console.log("Сервер ответил:", response);


                if (response.success) {
                    customers.push({
                        id: response.newUserId || Math.floor(Math.random() * 9999) + 1000,
                        name: userData.userName,
                        email: userData.email,
                        accon: accon,
                        avatar: avatar
                    });

                    renderTable(customers);
                    showNotification('Пользователь успешно добавлен!');
                } else {
                    throw new Error(response.error || 'Неизвестная ошибка от сервера');
                }

            } catch (error) {
                console.error("Ошибка при добавлении пользователя:", error);
                showNotification(`Не удалось добавить пользователя: ${error.message}`);
                return;
            }

        }

        this.reset();
        avatarDataUrl = "";
        avatarPreview.innerHTML = `<span class="camera-icon">
        <img src="./static/ima/phot.svg" alt="pht" />
    </span>`;
        document.getElementById('addCustomerModal').classList.remove('open');
    });

    window.editCustomer = function(idx) {
        editIndex = idx;
        const c = customers[idx];
        let [firstName, ...lastNameArr] = c.name.split(' ');
        let lastName = lastNameArr.join(' ');

        document.getElementById('addCustomerModal').classList.add('open');

        const form = document.getElementById('addCustomerForm');
        form.firstName.value = firstName;
        form.lastName.value = lastName;
        form.email.value = c.email;
        form.accon.value = c.accon;

        avatarDataUrl = c.avatar;
        if (c.avatar.startsWith('data:')) {
            avatarPreview.innerHTML = `<img src="${c.avatar}" alt="Avatar">`;
        } else {
            avatarPreview.innerHTML = `<img src="${c.avatar}" alt="Avatar">`;
        }
    }

    window.confirmDelete = function(idx) {
        const customer = customers[idx];
        if (customer) {
            itemToDelete = customer;
            document.getElementById('confirmModal').classList.add('show');
        } else {
            console.error("Не удалось найти пользователя для удаления по индексу:", idx);
            showNotification("Произошла ошибка. Не удалось найти пользователя.");
        }
    }


    document.getElementById('confirmDeleteBtn').onclick = async function() {
        if (!itemToDelete) return;

        const customerId = itemToDelete.id;
        const cameraId = localStorage.getItem('cameraId');

        if (!cameraId) {
            alert(localStorage.getItem('cameraId'));
            showNotification("Ошибка: ID камеры не найден. Невозможно удалить пользователя.");

            return;
        }


        const deleteData = {
            sub_action: 'delete',
            account_id: customerId,
            camera_id: cameraId
        };

        try {
            console.log(deleteData);
            const response = await wsClient.sendWithResponse('manage_account', deleteData);

            console.log("Сервер ответил на удаление:", response);
            const indexInArray = customers.findIndex(c => c.id === customerId);
            if (indexInArray > -1) {
                customers.splice(indexInArray, 1);
                renderTable(customers);
                showNotification('Пользователь успешно удален.');
            }

        } catch (error) {
            console.error("Ошибка при удалении пользователя:", error);
            showNotification(`Не удалось удалить пользователя: ${error.message}`);
        } finally {

            itemToDelete = null;
            document.getElementById('confirmModal').classList.remove('show');
        }
    };

    document.getElementById('cancelDeleteBtn').onclick = function() {
        itemToDelete = null;
        document.getElementById('confirmModal').classList.remove('show');
    };
    document.getElementById('cancelDeleteBtn').onclick = function() {
        deleteIndex = null;
        document.getElementById('confirmModal').classList.remove('show');
    }
    const token = localStorage.getItem('auth_token')
    if (!token) {
        window.location.href = '/login';
        return;
    }
    class WebSocketClient {
        constructor() {
            this.ws = null;
            this.reconnectInterval = 5000;
            this.shouldReconnect = true;
            this.messageQueue = [];
            this.responseHandlers = new Map();
            this.messageId = 0;
            this.connect();
        }

        connect() {
            try {
                this.ws = new WebSocket('ws://127.0.0.1:8005/ws');
                this.ws.onopen = () => {
                    console.log('WebSocket подключен');
                    const cameraId = localStorage.getItem('cameraId');
                    this.ws.send(JSON.stringify({
                        type: 'xto_ya',
                        token: token,
                    }));
                    this.ws.send(JSON.stringify({
                        type: 'spisok_inf',
                        data: {
                            camera_id: cameraId
                        }
                    }));
                    console.log('Запросили файлы');
                };

                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        console.log('Получено сообщение от сервера:', data);
                        if (data.ok === 'False') {
                            setTimeout(() => {
                                window.location.href = '/login';
                            }, 1500);
                        }
                        const action = data.action;
                        let requestType = '';
                        if (action === 'register_success' || action === 'register_failed') {
                            requestType = 'register';
                        } else if (action === 'account_deleted' || action === 'account_edited' || (data.source_action === 'manage_account' && action === 'error')) {
                            requestType = 'manage_account';
                        }

                        if (requestType && this.responseHandlers.has(requestType)) {
                            const handlers = this.responseHandlers.get(requestType);

                            if (data.success || action.includes('_success') || action === 'account_deleted') {
                                handlers.resolve(data);
                            } else {
                                handlers.reject(new Error(data.error || 'Произошла ошибка на сервере'));
                            }

                            this.responseHandlers.delete(requestType);
                            return;
                        }


                        switch (action) {
                            case 'spisok_list':
                                if (data.data && Array.isArray(data.data)) {
                                    userListData = data.data.map(serverUser => {
                                        const roleText = serverUser.role === 'moderator' ? 'Админ' : 'Ученик';
                                        const avatarSrc = serverUser.image ? serverUser.image : `static/ima/ic3.svg`;
                                        return {
                                            id: serverUser.id,
                                            name: serverUser.username,
                                            email: serverUser.email || serverUser.mail || 'Не указана',
                                            accon: roleText,
                                            avatar: avatarSrc,
                                        };
                                    });
                                    mergeAndRenderData();
                                }
                                break;

                            case 'spisok_info_list':
                                if (data.data && Array.isArray(data.data)) {

                                    userInfoData = data.data;

                                    mergeAndRenderData();
                                }
                                break;

                            default:
                                console.warn(`Получено необработанное сообщение с действием: ${action}`);
                        }
                    } catch (error) {
                        console.error('Ошибка обработки сообщения от WebSocket:', error);
                    }
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket ошибка:', error);
                    connectionStatus.textContent = "Отключено";
                    connectionStatus.classList.remove("connected");
                    connectionStatus.classList.add("disconnected");

                    this.responseHandlers.forEach((handlers) => {
                        handlers.reject(new Error('Ошибка соединения'));
                    });
                    this.responseHandlers.clear();
                };

                this.ws.onclose = () => {
                    console.log('WebSocket отключен');

                    this.responseHandlers.forEach((handlers) => {
                        handlers.reject(new Error('Соединение закрыто'));
                    });
                    this.responseHandlers.clear();

                    if (this.shouldReconnect) {
                        setTimeout(() => this.connect(), this.reconnectInterval);
                    }
                };
            } catch (error) {
                console.error('Ошибка подключения WebSocket:', error);
                if (this.shouldReconnect) {
                    setTimeout(() => this.connect(), this.reconnectInterval);
                }
            }
        }

        sendWithResponse(type, data) {
            return new Promise((resolve, reject) => {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {

                    this.responseHandlers.set(type, {
                        resolve,
                        reject
                    });

                    this.ws.send(JSON.stringify({
                        type: type,
                        data: {
                            ...data,
                        }
                    }));

                    setTimeout(() => {
                        if (this.responseHandlers.has(type)) {
                            this.responseHandlers.delete(type);
                            reject(new Error('Превышено время ожидания ответа от сервера'));
                        }
                    }, 30000);
                } else {

                    this.messageQueue.push({
                        data: {
                            type,
                            data
                        },
                        resolve,
                        reject
                    });
                }
            });
        }

        disconnect() {
            this.shouldReconnect = false;
            if (this.ws) {
                this.ws.close();
            }
        }


    }

    const wsClient = new WebSocketClient();
    const messageContainer = document.getElementById('message');

    function generateInviteCode() {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        let result = '';
        for (let i = 0; i < 5; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }

    const createCodeBtn = document.getElementById('createCodeBtn');
    const originalButtonText = createCodeBtn.textContent;

    let isCodeDisplayed = false;
    let resetTimer = null;

    function fallbackCopyTextToClipboard(text) {
        const textArea = document.createElement("textarea");
        textArea.value = text;

        textArea.style.top = "0";
        textArea.style.left = "0";
        textArea.style.position = "fixed";

        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            const successful = document.execCommand('copy');
            const msg = successful ? 'successful' : 'unsuccessful';
            console.log('Fallback: Copying text command was ' + msg);
            return Promise.resolve();
        } catch (err) {
            console.error('Fallback: Oops, unable to copy', err);
            return Promise.reject(err);
        } finally {
            document.body.removeChild(textArea);
        }
    }

    function generateInviteCode() {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        let result = '';
        for (let i = 0; i < 5; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }

    createCodeBtn.addEventListener('click', () => {

        if (isCodeDisplayed) {
            const codeToCopy = createCodeBtn.textContent;

            const copyPromise = navigator.clipboard ?
                navigator.clipboard.writeText(codeToCopy) :
                fallbackCopyTextToClipboard(codeToCopy);

            copyPromise.then(() => {
                console.log(`Код "${codeToCopy}" скопирован в буфер обмена.`);
                createCodeBtn.textContent = 'Скопировано!';
                setTimeout(() => {
                    if (isCodeDisplayed) {
                        createCodeBtn.textContent = codeToCopy;
                    }
                }, 1500);
            }).catch(err => {
                console.error('Ошибка: не удалось скопировать код. ', err);
                showNotification('Не удалось скопировать код.');
            });

            return;
        }

        clearTimeout(resetTimer);

        const cameraId = localStorage.getItem('cameraId');
        if (!cameraId) {
            showNotification('Ошибка: Camera ID не найден. Невозможно создать код.');
            console.error('Camera ID is not found in localStorage.');
            return;
        }

        if (wsClient && wsClient.ws && wsClient.ws.readyState === WebSocket.OPEN) {
            const newCode = generateInviteCode();

            wsClient.ws.send(JSON.stringify({
                type: 'generate_invite_code',
                data: {
                    code: newCode,
                    cameraId: cameraId
                }
            }));
            console.log(`Отправлен код ${newCode} для камеры ${cameraId} на сервер`);

            createCodeBtn.textContent = newCode;
            createCodeBtn.classList.add('code-displayed');
            isCodeDisplayed = true;

            resetTimer = setTimeout(() => {
                createCodeBtn.textContent = originalButtonText;
                createCodeBtn.classList.remove('code-displayed');
                isCodeDisplayed = false;
            }, 5000);

        } else {
            console.error('Не удалось отправить код. WebSocket не подключен.');
            showNotification('Ошибка: соединение с сервером не установлено.');
        }
    });

    function logout() {
        localStorage.clear();
        window.location.href = "/login";
    }
    renderTable(customers);
    updateUI();

});