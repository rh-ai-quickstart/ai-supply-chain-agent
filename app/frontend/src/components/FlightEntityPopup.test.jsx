import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FlightEntityPopup } from "./FlightEntityPopup";

describe("FlightEntityPopup", () => {
  const indexes = buildIndexes();

  it("shows company, cargo, and linked SKUs for a flight", () => {
    render(
      <FlightEntityPopup
        info={{
          id: "flight-a",
          callSign: "BAW177",
          route: "LHR-JFK",
          originCountry: "United Kingdom",
          status: "airborne",
          companyId: "company-1",
          companyName: "Acme Logistics",
          revenueUsd: 680000,
        }}
        valueByEntity={new Map()}
        affectedIds={[]}
        currency="USD"
        supplyChainIndexes={indexes}
        isHighlighted={false}
      />,
    );

    expect(screen.getByText("BAW177")).toBeInTheDocument();
    expect(screen.getByText("Acme Logistics")).toBeInTheDocument();
    expect(screen.getByText("(company-1)")).toBeInTheDocument();
    expect(screen.getByText(/Cargo on board \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText("pharmaceuticals")).toBeInTheDocument();
    expect(screen.getByText(/Linked SKUs \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText("SKU-PHARMA-01")).toBeInTheDocument();
  });
});

function buildIndexes() {
  const cargoByCarrier = new Map([
    [
      "flight-a",
      [
        {
          id: "cargo-a-1",
          type: "cargo_item",
          attributes: {
            commodity: "pharmaceuticals",
            quantity: 8,
            unit_price_usd: 8500,
            value_usd: 68000,
            sku_ref: "sku-pharma-01",
          },
        },
      ],
    ],
  ]);
  const skusByCarrier = new Map([
    [
      "flight-a",
      [
        {
          id: "sku-pharma-01",
          type: "inventory_sku",
          attributes: {
            sku: "SKU-PHARMA-01",
            commodity: "pharmaceuticals",
            warehouse_id: "warehouse-inland-empire",
            on_hand_qty: 24,
            unit_price_usd: 8500,
            value_usd: 204000,
          },
        },
      ],
    ],
  ]);
  return { cargoByCarrier, skusByCarrier };
}
