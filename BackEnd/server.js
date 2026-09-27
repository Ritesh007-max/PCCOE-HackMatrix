const path = require("path");

require("dotenv").config({
    path: path.join(__dirname, ".env")
});

const app = require("./src/app");

const port = process.env.PORT || 5000;
const host = "0.0.0.0";

app.listen(port, host, () => {
    console.log(`Server is running on http://${host}:${port}`);
});