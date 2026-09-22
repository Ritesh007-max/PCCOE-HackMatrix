const schemeServices = require("../services/schemeServices");

const listSchemes = async (req, res, next) => {
    try {
        const { category, state, status, keyword, q } = req.query;
        const data = await schemeServices.listSchemes({
            category,
            state,
            status,
            keyword: keyword || q
        });

        res.json({
            success: true,
            count: data.length,
            filters: {
                category: category || null,
                state: state || null,
                status: status || null,
                keyword: keyword || q || null
            },
            data
        });
    } catch (error) {
        next(error);
    }
};

const getScheme = async (req, res, next) => {
    try {
        const scheme = await schemeServices.getSchemeById(req.params.id);
        res.json({ success: true, data: scheme });
    } catch (error) {
        next(error);
    }
};

module.exports = {
    listSchemes,
    getScheme
};
