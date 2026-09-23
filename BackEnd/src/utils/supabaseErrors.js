const throwIfError = (error, fallbackStatus = 500) => {
    if (!error) {
        return;
    }

    const err = new Error(error.message);
    err.status = fallbackStatus;
    throw err;
};

module.exports = { throwIfError };
