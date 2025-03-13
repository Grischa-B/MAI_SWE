workspace "PlanTasks" {
    model {
        user = person "User" "Системный пользователь"

        system = softwareSystem "Task Planner" "Управление целями, задачами и пользователями" {
            web = container "Web UI" "Пользовательский интерфейс" "React"
            userSvc = container "User Service" "Сервис управления пользователями" ".NET"
            goalSvc = container "Goal Service" "Сервис управления целями" ".NET"
            taskSvc = container "Task Service" "Сервис управления задачами" ".NET"
            db = container "Database" "Хранилище данных" "PostgreSQL"
        }

        auth = softwareSystem "Auth" "Внешняя система аутентификации"

        user -> web "Использует"
        web -> userSvc "Запрос User API" "HTTPS/JSON"
        web -> goalSvc "Запрос Goal API" "HTTPS/JSON"
        web -> taskSvc "Запрос Task API" "HTTPS/JSON"
        userSvc -> db "Читает/Записывает" "SQL"
        goalSvc -> db "Читает/Записывает" "SQL"
        taskSvc -> db "Читает/Записывает" "SQL"
        web -> auth "Запрос аутентификации" "HTTPS/JSON"
        taskSvc -> goalSvc "Обновляет цель" "REST"
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
        dynamic system "task_creation" {
            user -> web "Запрос на создание задачи"
            web -> taskSvc "Вызов Task API"
            taskSvc -> db "Сохраняет задачу"
            taskSvc -> goalSvc "Обновляет цель"
            goalSvc -> db "Сохраняет обновление"
            taskSvc -> web "Возвращает результат"
            web -> user "Показывает подтверждение"
        }
        theme default
    }
}
