workspace "TaskPlanning" {
    model {
        user = person "User" "Системный пользователь"

        system = softwareSystem "TaskPlanner" "Управление целями и задачами" {
            webUI = container "WebUI" "React-интерфейс" "React"
            userService = container "UserService" "REST API + Redis Cache" "FastAPI"
            goalService = container "GoalService" "REST API целей/задач" "FastAPI + MongoDB"
            postgresDB = container "PostgresDB" "Хранилище пользователей" "PostgreSQL 14"
            redisCache = container "RedisCache" "Кеш для UserService" "Redis 7"
            mongoDB = container "MongoDB" "Хранилище целей/задач" "MongoDB 5.0"
        }

        user -> webUI "Использует"
        webUI -> userService "API пользователей" "HTTPS/JSON"
        webUI -> goalService "API целей/задач" "HTTPS/JSON"
        userService -> postgresDB "CRUD пользователей" "SQL"
        userService -> redisCache "Cache Layer" "Redis Driver"
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
        dynamic system "user_readthrough" {
            user -> webUI "GET /users/{id}"
            webUI -> userService "Запрос пользователя"
            userService -> redisCache "Проверка в кеше"
            redisCache -> userService "Хит/Мисс"
            userService -> postgresDB "DB Read"
            postgresDB -> userService "Data"
            userService -> redisCache "Запись в кеш"
            userService -> webUI "200 OK"
            webUI -> user "Показывает результат"
        }
        theme default
    }
}
