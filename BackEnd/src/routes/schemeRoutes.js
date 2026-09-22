const express = require("express");
const schemeController = require("../controllers/schemeController");

const router = express.Router();

router.get("/", schemeController.listSchemes);
router.get("/:id", schemeController.getScheme);

module.exports = router;
