// 404 - Not Found Handler
const notFoundHandler = (req, res, next) => {
    res.status(404).json({
        success: false,
        message: "Route not found"
    });
};

// Global Error Handler
const globalErrorHandler = (error, req, res, next) => {
    console.error(error);

    const status = error.status || 500;
    res.status(status).json({
        success: false,
        message: status >= 500 ? "Internal server error" : (error.message || "Request failed")
    });
};

module.exports = {
    notFoundHandler,
    globalErrorHandler
};
