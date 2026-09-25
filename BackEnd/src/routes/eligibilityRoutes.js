const express = require('express');
const router = express.Router();

router.post('/check', (req, res) => {
    // Placeholder for eligibility check
    res.json({ success: true, message: 'Eligibility checked successfully', data: { eligible: true } });
});

module.exports = router;
