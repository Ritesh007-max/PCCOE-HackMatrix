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

    res.status(error.status || 500).json({
        success: false,
        message: error.message || "Internal server error"
    });
};

module.exports = {
    notFoundHandler,
    globalErrorHandler
};