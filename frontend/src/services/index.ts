// Runtime service selector.
// VITE_USE_MOCK defaults to mock (any value other than "false").
// At build time Vite replaces the env string so tree-shaking still works.
import * as mock from "./mock/index";
import * as api  from "./api/index";

const impl = import.meta.env.VITE_USE_MOCK === "false" ? api : mock;

export const getProducts        = impl.getProducts;
export const getProduct         = impl.getProduct;
export const getInventory       = impl.getInventory;
export const getInventoryItem   = impl.getInventoryItem;
export const getNotices         = impl.getNotices;
export const getNotice          = impl.getNotice;
export const getMatches         = impl.getMatches;
export const getMatch           = impl.getMatch;
export const getActionLogs      = impl.getActionLogs;
export const addActionLog       = impl.addActionLog;
export const runMatching        = impl.runMatching;
export const getDashboardSummary = impl.getDashboardSummary;
export const getRecentActivity  = impl.getRecentActivity;
export const getAttentionItems  = impl.getAttentionItems;

export const createProduct       = impl.createProduct;
export const updateProduct       = impl.updateProduct;
export const deleteProduct       = impl.deleteProduct;
export const createInventoryItem = impl.createInventoryItem;
export const updateInventoryItem = impl.updateInventoryItem;
export const deleteInventoryItem = impl.deleteInventoryItem;
export const createNotice        = impl.createNotice;
export const deleteNotice        = impl.deleteNotice;
