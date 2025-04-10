workspace "TaskPlanning" {
    model {
        // Пользователь системы
        user = person "User" "Системный пользователь"

        // Основная система — система управления целями, задачами и пользователями
        system = softwareSystem "TaskPlanner" "Система управления целями, задачами и пользователями" {
            webUI = container "WebUI" "Веб-интерфейс для взаимодействия с системой" "React"
            userService = container "UserService" "REST API для управления пользователями с JWT аутентификацией" "FastAPI"
            goalService = container "GoalService" "REST API для управления целями (и задачами) с JWT аутентификацией" "FastAPI"
            inMemoryDB = container "InMemoryDB" "Хранилище данных в памяти" "In-Memory"
        }

        // Внешняя система аутентификации (с использованием JWT)
        authentication = softwareSystem "Authentication" "Сервис аутентификации JWT"

        // Определение связей между элементами модели
        user -> webUI "Использует" 
        webUI -> userService "Вызов API пользователей" "HTTPS/JSON"
        webUI -> goalService "Вызов API целей" "HTTPS/JSON"
        userService -> inMemoryDB "Читает/Записывает данные" "SQL"
        goalService -> inMemoryDB "Читает/Записывает данные" "SQL"
        webUI -> authentication "Запрос аутентификации" "HTTPS/JSON"
    }

    views {
        // Диаграмма контекста системы
        systemContext system {
            include *
            autolayout lr
        }
        // Диаграмма контейнеров
        container system {
            include *
            autolayout lr
        }
        // Динамическая диаграмма для сценария создания цели
        dynamic system "goal_creation" {
            user -> webUI "Отправляет запрос на создание цели"
            webUI -> goalService "Вызов API для создания цели"
            goalService -> inMemoryDB "Сохраняет цель"
            goalService -> webUI "Возвращает подтверждение"
            webUI -> user "Отображает результат"
        }
        theme default
    }
}
