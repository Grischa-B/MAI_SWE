workspace "TaskPlanning" {
    model {
        user = person "User" "Системный пользователь"

        system = softwareSystem "TaskPlanner" "Управление целями и задачами" {
            webUI = container "WebUI" "React-интерфейс" "React"
            userService = container "UserService" "REST API пользователей" "FastAPI + PostgreSQL"
            goalService = container "GoalService" "REST API целей/задач" "FastAPI + MongoDB"
            postgresDB = container "PostgresDB" "Хранилище пользователей" "PostgreSQL 14"
            mongoDB    = container "MongoDB" "Хранилище целей/задач" "MongoDB 5.0"
        }

        user -> webUI "Использует"
        webUI -> userService "API пользователей" "HTTPS/JSON"
        webUI -> goalService "API целей/задач" "HTTPS/JSON"
        userService -> postgresDB "CRUD пользователей" "SQL"
        goalService -> mongoDB "CRUD целей/задач" "MongoDB Driver"
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
        dynamic system "goal_crud" {
            user -> webUI "Создать цель"
            webUI -> goalService "POST /goals"
            goalService -> mongoDB "insertOne"
            goalService -> webUI "200 OK"
            webUI -> user "Показывает результат"
        }
        theme default
    }
}
