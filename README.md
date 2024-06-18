1. Initialize database container

    ```sh
    docker run --name postgres -e POSTGRES_PASSWORD=<password> -p 5432:5432 -d ankane/pgvector

    ```

2. Create .env

    ```sh
    cp .env.example .env
    ```

3. Add keys:

    - `DATABASE_URL`: `postgresql://postgres:<password>@localhost:5432/postgres`
    - `NVIDIA_API_KEY`
    - `OPENAI_API_KEY`

4. Install backend dependencies and start server

    ```sh
    cd backend
    pip3 install -r requirements.txt
    cd app
    uvicorn main:app --reload
    ```

5. Do the same for frontend

    ```sh
    cd frontend
    npm install
    npm start
    ```
