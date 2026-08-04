import cv2
import mediapipe as mp

def main():
    # Проверим версию MediaPipe
    print("MediaPipe version:", mp.__version__)

    # Инициализируем модули
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    # Настройки (можно поиграть с параметрами)
    hands = mp_hands.Hands(
        static_image_mode=False,       # видеопоток
        max_num_hands=2,               # макс. число рук
        min_detection_confidence=0.5,  # порог детекции
        min_tracking_confidence=0.5    # порог трекинга
    )

    # Открываем первую камеру
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Не удалось открыть видеокамеру")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Переведём в RGB и передаём в MediaPipe
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)

        # Если нашли руки — отрисуем landmarks и связи
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(0,0,255), thickness=2)
                )

        # Показать результат
        cv2.imshow('MediaPipe Hands Test', frame)

        # Выход по клавише q
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()