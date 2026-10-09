const express = require("express");
const userRoutes = require("./routes/userRouter");
const profileRoutes = require("./routes/profileRouter");
const dashboardRoutes = require("./routes/dashboardRouter");
const documentRoutes = require("./routes/documentRoutes");
const schemeRoutes = require("./routes/schemeRoutes");
const eligibilityRoutes = require("./routes/eligibilityRoutes");
const chatRoutes = require("./routes/chatRoutes");
const applicationRoutes = require("./routes/applicationRoutes");
const reviewerRoutes = require("./routes/reviewerRoutes");
const notificationRoutes = require("./routes/notificationRoutes");
const { notFoundHandler, globalErrorHandler } = require("./middleware/errorHandler");

const { createCorsMiddleware } = require("./config/corsConfig");

const app = express();

app.use(createCorsMiddleware());
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
app.use("/api/reviewer", reviewerRoutes);
app.use("/api/notifications", notificationRoutes);
app.use(notFoundHandler);
app.use(globalErrorHandler);

module.exports = app;
