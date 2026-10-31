// Runtime service selector.
// Mock data is used only when VITE_USE_MOCK=true; API failures never fall back.
// At build time Vite replaces the env string so tree-shaking still works.
import * as mock from "./mock/index";
import * as api  from "./api/index";

export const isMockData = import.meta.env.VITE_USE_MOCK === "true";
const impl = (isMockData ? mock : api) as typeof mock;

export const getProducts        = impl.getProducts;
export const getProduct         = impl.getProduct;
export const getInventory       = impl.getInventory;
export const getInventoryItem   = impl.getInventoryItem;
export const getNotices         = impl.getNotices;
export const getNotice          = impl.getNotice;
export const getMatches         = impl.getMatches;
export const getMatch           = impl.getMatch;
export const getActionLogs      = impl.getActionLogs;
export const getActivity        = impl.getActivity;
export const addActionLog       = impl.addActionLog;
export const runMatching        = impl.runMatching;
export const getDashboardSummary = impl.getDashboardSummary;
export const getRecentActivity  = impl.getRecentActivity;
export const getAttentionItems  = impl.getAttentionItems;
export const getSyncStatus      = impl.getSyncStatus;
export const getSyncHistory     = impl.getSyncHistory;
export const getSyncRun         = impl.getSyncRun;
export const startThaiFdaSync   = impl.startThaiFdaSync;

export const createProduct       = impl.createProduct;
export const updateProduct       = impl.updateProduct;
export const deleteProduct       = impl.deleteProduct;
export const createInventoryItem = impl.createInventoryItem;
export const updateInventoryItem = impl.updateInventoryItem;
export const deleteInventoryItem = impl.deleteInventoryItem;
export const createNotice        = impl.createNotice;
export const deleteNotice        = impl.deleteNotice;
