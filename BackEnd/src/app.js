const express = require("express");
const cors = require("cors");
const userRoutes = require("./routes/userRouter");
const { notFoundHandler, globalErrorHandler } = require("./middleware/errorHandler");

const app = express();

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
    res.json({
        success: true,
        message: "Backend API is running"
    });
});

app.use("/api/users", userRoutes);
app.use(notFoundHandler);
app.use(globalErrorHandler);

module.exports = app;