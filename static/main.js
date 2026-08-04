import { obnaruz } from '/static/obn.js'



document.addEventListener('DOMContentLoaded', () => {
    const name = document.getElementById('user-name');

    const role = document.getElementById('user-role');
    const cameraid = localStorage.getItem('cameraId');
    const updateUI = () => {
        name.innerHTML = localStorage.getItem('username');
        role.innerHTML = localStorage.getItem('userRole');
    }
    const connectionStatus = document.getElementById("connectionStatus");
    const totalcount = document.getElementById("total-count")
    const flicklcount = document.getElementById("flick-count")
    const deprcount = document.getElementById("depr-count")
    const opozcount = document.getElementById("late-count")

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
                console.log('WebSocket запрос');
                this.ws = new WebSocket('ws://127.0.0.1:8005/ws');
                connectionStatus.textContent = "Подключено";
                connectionStatus.classList.remove("disconnected");
                connectionStatus.classList.add("connected");
                this.ws.onopen = () => {
                    console.log('WebSocket подключен');
                    this.ws.send(JSON.stringify({
                        type: 'xto_ya',
                        token: token,
                    }));
                    this.ws.send(JSON.stringify({
                        type: 'get_json_files',
                        data: {
                            camera_id: cameraid,
                        }
                    }));
                    console.log('Запросили файлы');

                    this.ws.send(JSON.stringify({
                        type: 'site_inf',
                        data: {
                            time: new Date().toISOString(),
                            camera: cameraid,
                        }

                    }));

                };

                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        const obnr = document.getElementById('live-detections');

                        console.log('Получено сообщение:', data);
                        if (data.ok === 'False') {
                            setTimeout(() => {
                                window.location.href = '/login';
                            }, 1500);
                        }
                        if (data.name) {
                            localStorage.setItem("username", data.name);
                            localStorage.setItem("userRole", data.role);
                        }
                        if (data.action === 'json_files_list') {

                            const todayData = data.files.find(item => item.today);
                            const obndata = data.files.find(item => item.obnaruz);
                            if (todayData && todayData.today.graf) {
                                const timeLabels = Object.keys(todayData.today.graf);
                                const visitorsData = Object.values(todayData.today.graf);

                                function easeInOutQuad(t, b, c, d) {
                                    t /= d / 2;
                                    if (t < 1) return c / 2 * t * t + b;
                                    t--;
                                    return -c / 2 * (t * (t - 2) - 1) + b;
                                }
                                const lineOptions = {
                                    chart: {
                                        type: 'line',
                                        stacked: true,
                                        height: 350,
                                        animations: {
                                            enabled: true,
                                            easing: 'easeInOutSine',
                                            speed: 800,
                                            dynamicAnimation: {
                                                enabled: true,
                                                speed: 800
                                            },
                                            animateGradually: {
                                                enabled: true,
                                                delay: 150
                                            }
                                        },
                                        events: {
                                            animationEnd: function(ctx) {}
                                        },
                                        toolbar: {
                                            show: true,
                                            tools: {
                                                download: true,
                                                selection: false,
                                                zoom: false,
                                                zoomin: false,
                                                zoomout: false,
                                                pan: false,
                                                reset: true,
                                                menu: true,
                                            },
                                        },
                                    },
                                    series: [{
                                        name: 'Учеников',
                                        data: visitorsData
                                    }],
                                    dataLabels: {
                                        enabled: false
                                    },
                                    xaxis: {
                                        categories: timeLabels,
                                        axisBorder: {
                                            show: false
                                        },
                                        axisTicks: {
                                            show: false
                                        },
                                        labels: {
                                            style: {
                                                colors: '#6B7280',
                                                fontSize: '12px'
                                            }
                                        }

                                    },
                                    yaxis: {

                                    },
                                    stroke: {
                                        curve: 'smooth',
                                        width: 4,
                                    },
                                    fill: {
                                        type: 'gradient',
                                        gradient: {
                                            shade: 'dark',
                                            colorStops: [{
                                                offset: 0,
                                                color: "#5BC4FF",
                                                opacity: 1
                                            }, {
                                                offset: 100,
                                                color: "#FF5BEF",
                                                opacity: 1
                                            }],
                                            shadeIntensity: 1,
                                            opacityFrom: 1,
                                            opacityTo: 1,

                                        }
                                    },
                                    yaxis: {
                                        tickAmount: 5,
                                        labels: {
                                            style: {
                                                colors: '#6B7280',
                                                fontSize: '12px'
                                            }
                                        },
                                        axisBorder: {
                                            show: false
                                        }
                                    },

                                    tooltip: {
                                        enabled: true,
                                        style: {
                                            fontSize: '12px'
                                        }
                                    },
                                };

                                Apex.animation = {
                                    easing: easeInOutQuad
                                };

                                const lineChart = new ApexCharts(document.querySelector("#attendanceChart"), lineOptions);
                                lineChart.render();
                                const namepie = 'total'
                                totalcount.innerHTML = todayData.today.person_total
                                deprcount.innerHTML = todayData.today.depr_total
                                flicklcount.innerHTML = todayData.today.flicker_total
                                opozcount.innerHTML = todayData.today.opoz_total

                                const pieOptions = {
                                    dataLabels: {
                                        enabled: false,
                                    },
                                    plotOptions: {
                                        pie: {
                                            expandOnClick: false,
                                            donut: {
                                                size: '60%',
                                                labels: {
                                                    show: true,
                                                    name: {

                                                    },
                                                    value: {

                                                    }
                                                }
                                            }
                                        }
                                    },
                                    chart: {
                                        type: 'donut',
                                        height: 350
                                    },
                                    series: [
                                        todayData.today.opoz_total,
                                        todayData.today.flicker_total,
                                        todayData.today.depr_total
                                    ],
                                    labels: ['Опозданий', 'Фликеров', 'Депресий'],
                                    legend: {
                                        position: 'bottom',
                                        horizontalAlign: 'center',
                                        fontSize: '13px',
                                        markers: {
                                            width: 12,
                                            height: 12,
                                            radius: 0
                                        },
                                        itemMargin: {
                                            horizontal: 10,
                                            vertical: 5
                                        }
                                    },
                                    responsive: [{
                                        breakpoint: 480,
                                        options: {
                                            legend: {
                                                position: 'bottom'
                                            }
                                        }
                                    }]
                                };

                                const pieChart = new ApexCharts(document.querySelector("#pieChart"), pieOptions);
                                pieChart.render();

                            }
                            if (obndata) {
                                console.log(obndata)
                                obnaruz(obndata, 'live-detections')
                            }
                        }

                        function loadJsonFiles() {
                            if (wsClient && wsClient.ws && wsClient.ws.readyState === WebSocket.OPEN) {
                                wsClient.ws.send(JSON.stringify({
                                    type: 'get_json_files',
                                    data: {
                                        camera_id: cameraid
                                    }
                                }));
                            }
                        }

                        function loadJsonContent(filename, filepath) {
                            if (wsClient && wsClient.ws && wsClient.ws.readyState === WebSocket.OPEN) {
                                wsClient.ws.send(JSON.stringify({
                                    type: 'get_json_content',
                                    data: {
                                        filename: filename,
                                        path: filepath,
                                        camera_id: cameraid
                                    }
                                }));
                                selectedJsonFile = filename;
                            }
                        }

                    } catch (error) {
                        console.error('Ошибка парсинга сообщения:', error);
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


    const classSelect = document.getElementById('class-select');
    const currentLessonBlock = document.getElementById('currentLesson');
    const noLessonsBlock = document.getElementById('noLessons');

    updateUI();


});