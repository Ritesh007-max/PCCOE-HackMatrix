const express = require("express");
const cors = require("cors");
const userRoutes = require("./routes/userRouter");
const profileRoutes = require("./routes/profileRouter");
const dashboardRoutes = require("./routes/dashboardRouter");
const documentRoutes = require("./routes/documentRoutes");
const schemeRoutes = require("./routes/schemeRoutes");
const eligibilityRoutes = require("./routes/eligibilityRoutes");
const chatRoutes = require("./routes/chatRoutes");
const applicationRoutes = require("./routes/applicationRoutes");
const { notFoundHandler, globalErrorHandler } = require("./middleware/errorHandler");

const app = express();

const allowedOrigins = (process.env.FRONTEND_ORIGINS || "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175")
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);

app.use(cors({
    origin(origin, callback) {
        // Allow requests with no origin (like mobile apps, curl, or server-to-server)
        if (!origin) return callback(null, true);
        
        // Allow explicitly configured origins or any localhost/127.0.0.1 port
        if (allowedOrigins.includes(origin) || /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)) {
            return callback(null, true);
        }
        
        return callback(new Error(`CORS error: Origin ${origin} not allowed`));
    },
    credentials: true,
    methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization", "X-Requested-With"]
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
app.use("/api/schemes", schemeRoutes);
app.use("/api/eligibility", eligibilityRoutes);
app.use("/api/chat", chatRoutes);
app.use("/api/applications", applicationRoutes);
app.use(notFoundHandler);
app.use(globalErrorHandler);

module.exports = app;
