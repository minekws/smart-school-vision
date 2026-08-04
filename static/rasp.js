document.addEventListener('DOMContentLoaded', function() {

    const dateDisplay = document.getElementById('date-display');
    const classSelect = document.getElementById('class-select');
    const scheduleList = document.getElementById('scheduleList');
    const currentLessonBlock = document.getElementById('currentLesson');
    const noLessonsBlock = document.getElementById('noLessons');

    let scheduleData = {};
    let todaySchedule = [];

    function formatTodayDate() {
        const today = new Date();
        const options = {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        };
        return `Сегодня, ${today.toLocaleDateString('ru-RU', options)}`;
    }

    function getRussianDayOfWeek() {
        const days = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота'];
        return days[new Date().getDay()];
    }

    async function loadSchedule() {
        try {

            scheduleList.innerHTML = `
                <div class="loading-message">
                    <div class="loading-spinner"></div>
                    <div>Загрузка расписания...</div>
                </div>
            `;

            const response = await fetch('/static/files/raspisanie.json');
            scheduleData = await response.json();
            console.log(response)

            populateClassSelect();

            if (classSelect.options.length > 0 && classSelect.options[0].value) {
                classSelect.value = classSelect.options[0].value;
                updateSchedule();
            }

        } catch (error) {
            console.error('Ошибка загрузки расписания:', error);
            showErrorMessage('Не удалось загрузить расписание');
        }
    }

    function populateClassSelect() {

        classSelect.innerHTML = '';
        const classes = Object.keys(scheduleData);

        if (classes.length > 0) {

            classes.sort((a, b) => {
                const numA = parseInt(a);
                const numB = parseInt(b);
                if (numA !== numB) return numA - numB;
                return a.localeCompare(b);
            });

            classes.forEach(className => {
                const option = document.createElement('option');
                option.value = className;
                option.textContent = className;
                classSelect.appendChild(option);
            });
        } else {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'Классы не найдены';
            option.disabled = true;
            option.selected = true;
            classSelect.appendChild(option);
            showErrorMessage('В расписании нет данных о классах');
        }
    }

    function showErrorMessage(message) {
        scheduleList.innerHTML = `
            <div class="error-message">
                <div class="error-icon">⚠️</div>
                <div class="error-text">${message}</div>
            </div>
        `;
    }

    function showNoScheduleMessage() {
        scheduleList.innerHTML = `
            <div class="no-schedule">
                <div class="no-schedule-icon">📅</div>
                <div class="no-schedule-text">Расписание на сегодня отсутствует</div>
            </div>
        `;
    }

    function updateSchedule() {

        if (Object.keys(scheduleData).length === 0) return;

        scheduleList.innerHTML = '';

        const selectedClass = classSelect.value;

        if (!selectedClass) {
            showNoScheduleMessage();
            return;
        }


        const dayOfWeek = getRussianDayOfWeek();

        if (dayOfWeek === 'воскресенье' || dayOfWeek === 'суббота') {
            showWeekendMessage();
            return;
        }

        if (scheduleData[selectedClass] && scheduleData[selectedClass][dayOfWeek]) {
            todaySchedule = scheduleData[selectedClass][dayOfWeek];

            if (todaySchedule.length > 0) {
                todaySchedule.forEach(lesson => {
                    const lessonElement = document.createElement('div');
                    lessonElement.className = 'schedule-item';
                    lessonElement.innerHTML = `
                        <div class="lesson-time">${lesson.time}</div>
                        <div class="lesson-info">
                            <div class="lesson-subject">${lesson.subject}</div>
                            <div class="lesson-teacher">${lesson.teacher}</div>
                        </div>
                        <div class="lesson-classroom">${lesson.classroom}</div>
                    `;
                    scheduleList.appendChild(lessonElement);
                });
            } else {
                showNoScheduleMessage();
            }
        } else {
            showNoScheduleMessage();
        }
        updateCurrentLesson();
    }

    function showWeekendMessage() {
        scheduleList.innerHTML = `
            <div class="no-schedule">
                <div class="no-schedule-icon">😊</div>
                <div class="no-schedule-text">Сегодня выходной!</div>
                <div class="no-schedule-subtext">Уроков нет</div>
            </div>
        `;
        currentLessonBlock.style.display = 'none';
        noLessonsBlock.style.display = 'none';
    }

    function updateCurrentLesson() {
        const now = new Date();
        const hours = now.getHours();
        const minutes = now.getMinutes();
        const currentTime = hours * 60 + minutes;

        const lessonElements = document.querySelectorAll('.schedule-item');
        lessonElements.forEach(item => {
            item.classList.remove('current');
        });

        let currentLesson = null;
        let lessonsEnded = true;

        todaySchedule.forEach((lesson, index) => {
            const timeParts = lesson.time.split(' - ');
            if (timeParts.length < 2) return;

            const [startHour, startMinute] = timeParts[0].split(':').map(Number);
            const [endHour, endMinute] = timeParts[1].split(':').map(Number);

            const startTime = startHour * 60 + startMinute;
            const endTime = endHour * 60 + endMinute;

            if (currentTime < endTime) {
                lessonsEnded = false;
            }

            if (currentTime >= startTime && currentTime <= endTime) {
                currentLesson = lesson;

                if (lessonElements[index]) {
                    lessonElements[index].classList.add('current');
                }
            }
        });

        if (currentLesson) {
            currentLessonBlock.querySelector('.current-subject').textContent = currentLesson.subject;
            currentLessonBlock.querySelector('.current-time').textContent = currentLesson.time;
            currentLessonBlock.querySelector('.current-classroom').textContent = currentLesson.classroom;
            currentLessonBlock.style.display = 'flex';
            noLessonsBlock.style.display = 'none';
        } else if (lessonsEnded) {
            currentLessonBlock.style.display = 'none';
            noLessonsBlock.style.display = 'flex';
        } else {
            currentLessonBlock.style.display = 'none';
            noLessonsBlock.style.display = 'none';
        }
    }

    classSelect.addEventListener('change', updateSchedule);
    dateDisplay.textContent = formatTodayDate();
    loadSchedule();

    setInterval(updateCurrentLesson, 60000);
    setInterval(() => {
        dateDisplay.textContent = formatTodayDate();
        updateSchedule();
    }, 300000);
});