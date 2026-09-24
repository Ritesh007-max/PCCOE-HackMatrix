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

    const uploadErrorStatus = error.name === 'MulterError'
        ? (error.code === 'LIMIT_FILE_SIZE' ? 413 : 400)
        : undefined;
    const status = error.status || uploadErrorStatus || 500;
    res.status(status).json({
        success: false,
        message: status >= 500
            ? "Internal server error"
            : (error.message || (status === 413 ? "Uploaded file is too large" : "Request failed"))
    });
};

module.exports = {
    notFoundHandler,
    globalErrorHandler
};
