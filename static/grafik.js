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
                        action: "grafiki",
                        data: {
                            camera_id: cameraid,
                            date_range: 7
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
                        if (data.action == "grafiki_data") {
                            const charts = data.charts;

                            if (charts.late_by_weekday) {
                                const lateChart = new ApexCharts(
                                    document.querySelector("#lateByWeekdayChart"), {
                                        chart: {
                                            type: 'bar',
                                            height: 350,
                                            stacked: charts.late_by_weekday.stacked,
                                            animations: {
                                                enabled: true,
                                                easing: 'easeinout',
                                                speed: 800
                                            }
                                        },
                                        series: charts.late_by_weekday.series,
                                        xaxis: {
                                            categories: charts.late_by_weekday.categories,
                                            labels: {
                                                style: {
                                                    colors: '#6B7280',
                                                    fontSize: '12px'
                                                }
                                            }
                                        },
                                        colors: ['#4CAF50', '#FF5252'],
                                        plotOptions: {
                                            bar: {
                                                horizontal: false,
                                                columnWidth: '55%',
                                                endingShape: 'rounded'
                                            }
                                        },
                                        dataLabels: {
                                            enabled: false
                                        },
                                        legend: {
                                            position: 'top',
                                            horizontalAlign: 'right'
                                        },
                                        fill: {
                                            opacity: 1
                                        },
                                        tooltip: {
                                            y: {
                                                formatter: function(val) {
                                                    return val + " учеников"
                                                }
                                            }
                                        }
                                    }
                                );
                                lateChart.render();
                            }

                            if (charts.flicker_pie) {
                                const flickerPieChart = new ApexCharts(
                                    document.querySelector("#flickerPieChart"), {
                                        chart: {
                                            type: 'donut',
                                            height: 350
                                        },
                                        series: charts.flicker_pie.data.map(item => item.value),
                                        labels: charts.flicker_pie.data.map(item => item.name),
                                        colors: charts.flicker_pie.data.map(item => item.color),
                                        plotOptions: {
                                            pie: {
                                                donut: {
                                                    size: '65%',
                                                    labels: {
                                                        show: true,
                                                        total: {
                                                            show: true,
                                                            label: 'Процент',
                                                            formatter: function() {
                                                                return charts.flicker_pie.percentage + '%';
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        },
                                        dataLabels: {
                                            enabled: true,
                                            formatter: function(val) {
                                                return Math.round(val) + "%"
                                            }
                                        },
                                        legend: {
                                            position: 'bottom'
                                        }
                                    }
                                );
                                flickerPieChart.render();
                            }

                            if (charts.flicker_dynamics) {
                                const dynamicsChart = new ApexCharts(
                                    document.querySelector("#flickerDynamicsChart"), {
                                        chart: {
                                            type: 'line',
                                            height: 350,
                                            animations: {
                                                enabled: true,
                                                easing: 'easeinout',
                                                speed: 800
                                            }
                                        },
                                        series: charts.flicker_dynamics.series,
                                        xaxis: {
                                            categories: charts.flicker_dynamics.categories,
                                            labels: {
                                                style: {
                                                    colors: '#6B7280',
                                                    fontSize: '12px'
                                                }
                                            }
                                        },
                                        yaxis: {
                                            min: charts.flicker_dynamics.y_axis.min,
                                            max: charts.flicker_dynamics.y_axis.max,
                                            labels: {
                                                formatter: function(val) {
                                                    return val + "%"
                                                }
                                            }
                                        },
                                        stroke: {
                                            curve: 'smooth',
                                            width: 3
                                        },
                                        colors: ['#00BCD4'],
                                        markers: {
                                            size: 5,
                                            hover: {
                                                size: 7
                                            }
                                        },
                                        fill: {
                                            type: 'gradient',
                                            gradient: {
                                                shadeIntensity: 1,
                                                opacityFrom: 0.7,
                                                opacityTo: 0.3,
                                                stops: [0, 90, 100]
                                            }
                                        },
                                        tooltip: {
                                            y: {
                                                formatter: function(val) {
                                                    return val + "%"
                                                }
                                            }
                                        }
                                    }
                                );
                                dynamicsChart.render();
                            }

                            if (charts.emotional_climate) {
                                const emotionalChart = new ApexCharts(
                                    document.querySelector("#emotionalClimateChart"), {
                                        chart: {
                                            type: 'bar',
                                            height: 350
                                        },
                                        plotOptions: {
                                            bar: {
                                                horizontal: true,
                                                distributed: true,
                                                dataLabels: {
                                                    position: 'bottom'
                                                }
                                            }
                                        },
                                        series: charts.emotional_climate.series,
                                        xaxis: {
                                            categories: charts.emotional_climate.categories
                                        },
                                        colors: charts.emotional_climate.series[0].colors,
                                        dataLabels: {
                                            enabled: true,
                                            textAnchor: 'start',
                                            style: {
                                                colors: ['#fff']
                                            },
                                            formatter: function(val) {
                                                return val
                                            },
                                            offsetX: 0
                                        },
                                        legend: {
                                            show: false
                                        }
                                    }
                                );
                                emotionalChart.render();
                            }

                            if (charts.emotion_index) {
                                const emotionIndexChart = new ApexCharts(
                                    document.querySelector("#emotionIndexChart"), {
                                        chart: {
                                            type: 'area',
                                            height: 350,
                                            animations: {
                                                enabled: true,
                                                easing: 'easeinout',
                                                speed: 800
                                            }
                                        },
                                        series: charts.emotion_index.series,
                                        xaxis: {
                                            categories: charts.emotion_index.categories
                                        },
                                        yaxis: {
                                            min: charts.emotion_index.y_axis.min,
                                            max: charts.emotion_index.y_axis.max,
                                            tickAmount: 5,
                                            labels: {
                                                formatter: function(val) {
                                                    if (val <= 33) return "Негативный";
                                                    if (val <= 66) return "Нейтральный";
                                                    return "Позитивный";
                                                }
                                            }
                                        },
                                        stroke: {
                                            curve: 'smooth',
                                            width: 3
                                        },
                                        fill: {
                                            type: 'gradient',
                                            gradient: {
                                                shadeIntensity: 1,
                                                opacityFrom: 0.7,
                                                opacityTo: 0.3,
                                                colorStops: [{
                                                        offset: 0,
                                                        color: "#9C27B0",
                                                        opacity: 1
                                                    },
                                                    {
                                                        offset: 100,
                                                        color: "#E91E63",
                                                        opacity: 1
                                                    }
                                                ]
                                            }
                                        },
                                        markers: {
                                            size: 5,
                                            hover: {
                                                size: 7
                                            }
                                        },
                                        tooltip: {
                                            y: {
                                                formatter: function(val) {
                                                    return "Индекс: " + val
                                                }
                                            }
                                        }
                                    }
                                );
                                emotionIndexChart.render();
                            }

                            if (charts.safety_time_correlation) {
                                const safetyChart = new ApexCharts(
                                    document.querySelector("#safetyTimeChart"), {
                                        chart: {
                                            type: 'bar',
                                            height: 350,
                                            stacked: true
                                        },
                                        series: charts.safety_time_correlation.series,
                                        xaxis: {
                                            categories: charts.safety_time_correlation.categories
                                        },
                                        colors: ['#4CAF50', '#FF9800'],
                                        plotOptions: {
                                            bar: {
                                                horizontal: false,
                                                columnWidth: '60%'
                                            }
                                        },
                                        dataLabels: {
                                            enabled: charts.safety_time_correlation.show_percentage,
                                            formatter: function(val, opt) {
                                                const total = opt.w.globals.stackedSeriesTotals[opt.dataPointIndex];
                                                const percent = Math.round((val / total) * 100);
                                                return percent + '%';
                                            }
                                        },
                                        legend: {
                                            position: 'top'
                                        },
                                        fill: {
                                            opacity: 1
                                        },
                                        tooltip: {
                                            y: {
                                                formatter: function(val) {
                                                    return val + " учеников"
                                                }
                                            }
                                        }
                                    }
                                );
                                safetyChart.render();
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

    function logout() {
        wsClient.ws.send(JSON.stringify({
            type: 'logout',
        }));
        localStorage.clear();
        sessionStorage.clear();
    }
    const classSelect = document.getElementById('class-select');
    const currentLessonBlock = document.getElementById('currentLesson');
    const noLessonsBlock = document.getElementById('noLessons');

    function logout() {
        localStorage.clear();
        window.location.href = "/login";
    }
    updateUI();
});