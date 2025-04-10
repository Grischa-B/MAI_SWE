workspace "TaskPlanning" {
    model {
        // Пользователь системы
        user = person "User" "Системный пользователь"

        // Основная система
        system = softwareSystem "TaskPlanner" "Система управления целями, задачами и пользователями" {
            webUI = container "WebUI" "Веб-интерфейс для взаимодействия с системой" "React"
            userService = container "UserService" "REST API для управления пользователями с JWT аутентификацией и PostgreSQL" "FastAPI"
            goalService = container "GoalService" "REST API для управления целями с JWT аутентификацией" "FastAPI"
            postgresDB = container "PostgresDB" "Постоянное хранилище данных" "PostgreSQL 14"
        }

        // Внешняя система аутентификации
        authentication = softwareSystem "Authentication" "Сервис аутентификации JWT"

        user -> webUI "Использует" 
        webUI -> userService "Вызов API пользователей" "HTTPS/JSON"
        webUI -> goalService "Вызов API целей" "HTTPS/JSON"
        userService -> postgresDB "Читает/Записывает данные" "SQL"
        goalService -> postgresDB "Читает/Записывает данные" "SQL"
        webUI -> authentication "Запрос аутентификации" "HTTPS/JSON"
    }

    views {
        systemContext system {
            include *
            autolayout lr
        }
        container system {
            include *
            autolayout lr
        }
        dynamic system "goal_creation" {
            user -> webUI "Отправляет запрос на создание цели"
            webUI -> goalService "Вызов API для создания цели"
            goalService -> postgresDB "Сохраняет цель"
            goalService -> webUI "Возвращает подтверждение"
            webUI -> user "Отображает результат"
        }
        theme default
    }
}
