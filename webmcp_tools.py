"""Read-only WebMCP tools for the authenticated Arsenal Sport app."""
import streamlit as st
import streamlit.components.v2 as components

_WEBMCP_COMPONENT = components.component(
    name="arsenal_sport_webmcp",
    html="<div aria-hidden='true'></div>",
    js=r"""
import { defineTool, registerTools } from "https://cdn.jsdelivr.net/npm/@nekuda/webmcp-sdk@0.7.1/dist/index.js";

globalThis.__WEBMCP_TELEMETRY__ = false;

const searchProducts = defineTool({
  stableKey: "catalog.search",
  name: "search_products",
  description: "Search the authenticated store catalog. Use for product discovery. Returns matching products and a count.",
  inputSchema: {
    type: "object",
    properties: {
      query: { type: "string", description: "Product name, brand, category, sport, or description term." },
      limit: { type: "integer", minimum: 1, maximum: 20, default: 10 }
    },
    required: ["query"],
    additionalProperties: false
  },
  annotations: { readOnlyHint: true },
  intent: "answer",
  source: "merchant_authored",
  async execute({ query, limit = 10 }) {
    const rows = globalThis.__ARSENAL_WEBMCP_DATA__?.products || [];
    const needle = String(query || "").trim().toLowerCase();
    if (!needle) throw new Error("Provide a non-empty product search term.");
    const fields = ["name", "brand", "category", "sport", "description", "size"];
    const products = rows.filter(row =>
      fields.some(field => String(row?.[field] ?? "").toLowerCase().includes(needle))
    ).slice(0, Math.min(20, Math.max(1, Number(limit) || 10)));
    return { products, count: products.length, note: products.length ? undefined : "The store has no matching catalog content." };
  }
});

const getProduct = defineTool({
  stableKey: "catalog.get_product",
  name: "get_product",
  description: "Read one authenticated catalog product by stable record ID or exact name. Returns the product or a not-found note.",
  inputSchema: {
    type: "object",
    properties: {
      record_id: { type: "string" },
      name: { type: "string" }
    },
    additionalProperties: false
  },
  annotations: { readOnlyHint: true },
  intent: "answer",
  source: "merchant_authored",
  async execute({ record_id, name }) {
    const rows = globalThis.__ARSENAL_WEBMCP_DATA__?.products || [];
    const id = String(record_id || "").trim();
    const wanted = String(name || "").trim().toLowerCase();
    const product = rows.find(row =>
      (id && String(row?._saas_record_id || "") === id) ||
      (wanted && String(row?.name || "").trim().toLowerCase() === wanted)
    );
    return product ? { product } : { product: null, note: "The store has no matching product." };
  }
});

const getStoreContext = defineTool({
  stableKey: "store.get_context",
  name: "get_store_context",
  description: "Read non-secret business settings and current catalog/content counts for the authenticated store.",
  inputSchema: { type: "object", properties: {}, additionalProperties: false },
  annotations: { readOnlyHint: true },
  intent: "answer",
  source: "merchant_authored",
  async execute() {
    const data = globalThis.__ARSENAL_WEBMCP_DATA__ || {};
    return {
      settings: data.settings || {},
      counts: {
        products: Array.isArray(data.products) ? data.products.length : 0,
        content_plan: Array.isArray(data.content_plan) ? data.content_plan.length : 0
      }
    };
  }
});

const getContentPlan = defineTool({
  stableKey: "content.get_plan",
  name: "get_content_plan",
  description: "Read the authenticated store's current content plan. Returns plan items and an explicit empty note when there are none.",
  inputSchema: { type: "object", properties: {}, additionalProperties: false },
  annotations: { readOnlyHint: true },
  intent: "answer",
  source: "merchant_authored",
  async execute() {
    const rows = globalThis.__ARSENAL_WEBMCP_DATA__?.content_plan || [];
    return { content_plan: rows, note: rows.length ? undefined : "The store has no content-plan items." };
  }
});

export default function(component) {
  globalThis.__ARSENAL_WEBMCP_DATA__ = component.data || {};
  const registration = registerTools(
    [searchProducts, getProduct, getStoreContext, getContentPlan],
    { telemetry: false }
  );
  return () => registration.unregister();
}
"""
)

def _webmcp_data():
    def safe_product(row):
        if not isinstance(row, dict):
            return row
        allowed = ("_saas_record_id", "name", "brand", "category", "sport", "description", "size", "stock")
        return {k: row.get(k) for k in allowed if k in row}

    try:
        settings_rows = data_load("settings", [])
    except Exception:
        settings_rows = []
    raw_settings = settings_rows[0] if settings_rows and isinstance(settings_rows[0], dict) else {}
    settings = {
        k: raw_settings.get(k)
        for k in ("business_type", "city", "telegram", "instagram", "shipping", "goal", "positioning")
        if k in raw_settings
    }

    try:
        products = [safe_product(row) for row in data_load("products", [])]
    except Exception:
        products = []
    try:
        raw_plan = data_load("content_plan", [])
        allowed_plan = ("content_id", "_saas_record_id", "date", "platform", "product", "type", "idea", "status", "priority")
        content_plan = [
            {k: row.get(k) for k in allowed_plan if k in row}
            for row in raw_plan
            if isinstance(row, dict)
        ]
    except Exception:
        content_plan = []

    return {"settings": settings, "products": products, "content_plan": content_plan}

def mount_webmcp_tools():
    _WEBMCP_COMPONENT(data=_webmcp_data(), key="arsenal-sport-webmcp")
