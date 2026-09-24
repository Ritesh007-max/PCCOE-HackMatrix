const express = require("express");
const cors = require("cors");
const userRoutes = require("./routes/userRouter");
const profileRoutes = require("./routes/profileRouter");
const dashboardRoutes = require("./routes/dashboardRouter");
const documentRoutes = require("./routes/documentRoutes");
const { notFoundHandler, globalErrorHandler } = require("./middleware/errorHandler");

const app = express();

const allowedOrigins = (process.env.FRONTEND_ORIGINS || "http://localhost:5173")
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);

app.use(cors({
    origin(origin, callback) {
        if (!origin || allowedOrigins.includes(origin)) return callback(null, true);
        return callback(null, false);
    }
}));
app.use(express.json());

app.get("/", (req, res) => {
    res.json({
        success: true,
        message: "Backend API is running"
    });
});

app.use("/api/users", userRoutes);
app.use("/api/users", profileRoutes);
app.use("/api/dashboard", dashboardRoutes);
app.use("/api/documents", documentRoutes);
app.use(notFoundHandler);
app.use(globalErrorHandler);

module.exports = app;
