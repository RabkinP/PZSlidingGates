-- Data shared by gameplay, construction and the future server controller.
-- Existing type IDs are saved in modData: keep them stable.
SGGateTypes = {
    chainlink = {
        entity = "SlidingGateChainLink2",
        width = 2,
        baseHealth = 300,
        materials = { ["Base.MetalPipe"] = 6, ["Base.Wire"] = 4, ["Base.ScrapMetal"] = 2, ["Base.SmallSheetMetal"] = 1, ["Base.Screws"] = 4 },
        clipSeconds = 3.0,
        leafModel = "SG_ChainLink_N_Right_G",
        doorSprites = { "fixtures_doors_fences_01_129", "fixtures_doors_fences_01_131" },
    },
    chainlink4 = {
        entity = "SlidingGateChainLink4",
        width = 4,
        baseHealth = 450,
        materials = { ["Base.MetalPipe"] = 10, ["Base.Wire"] = 8, ["Base.ScrapMetal"] = 3, ["Base.SmallSheetMetal"] = 2, ["Base.Screws"] = 4 },
        clipSeconds = 6.0,
        leafModel = "SG_ChainLink_4_N_Right_G",
        doorSprites = { "fixtures_doors_fences_01_129", "fixtures_doors_fences_01_131" },
    },
}
