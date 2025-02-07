


### 1. Register at research agent

```bash
curl --location '127.0.0.1:8080/register'
```

### 2. Register at search agent

```bash
curl --location '127.0.0.1:8081/register'
```

### 3. Requesting 

```bash
curl --location '127.0.0.1:8081/search' \
--header 'Content-Type: application/json' \
--data '{
    "query": "I want assistance with my research work",
    "prompt": "Any research paper publish on blockchain"
}'
```
