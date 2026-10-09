const path = require("path");

require("dotenv").config({
    path: path.join(__dirname, ".env")
});

const app = require("./src/app");

const port = process.env.PORT || 5000;

app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});
// Nodemon reload trigger