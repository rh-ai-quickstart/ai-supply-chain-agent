import PropTypes from "prop-types";
import {
  buildFlightPopupValues,
  cargoLineValue,
  formatCommodityLabel,
  formatCurrency,
  skuInventoryValue,
} from "../utils/impactEntityUtils";

function DetailRow({ label, value, strong = false }) {
  if (value == null || value === "") return null;
  return (
    <div className="flight-popup-row">
      <span className="flight-popup-label">{label}</span>
      <span className={strong ? "flight-popup-value-strong" : "flight-popup-value"}>{value}</span>
    </div>
  );
}

DetailRow.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.node,
  strong: PropTypes.bool,
};

export function FlightEntityPopup({
  info,
  valueByEntity,
  affectedIds,
  currency,
  supplyChainIndexes,
  isHighlighted,
}) {
  const {
    cargo,
    skus,
    flightValue,
    displayCargoTotal,
    totalAtRisk,
    showTotal,
  } = buildFlightPopupValues(info, valueByEntity, affectedIds, supplyChainIndexes);

  const title = info.callSign || info.id;
  const companyLabel = info.companyName || info.companyId;

  return (
    <div className="flight-popup">
      <header className="flight-popup-header">
        <div className="flight-popup-title-row">
          <h3 className="flight-popup-title">{title}</h3>
          <span className="flight-popup-badge">Flight</span>
        </div>
        {companyLabel ? (
          <p className="flight-popup-company">
            <span className="flight-popup-company-label">Company</span>
            <span className="flight-popup-company-value">{companyLabel}</span>
            {info.companyName && info.companyId ? (
              <span className="flight-popup-company-id muted">({info.companyId})</span>
            ) : null}
          </p>
        ) : null}
        {info.id && info.id !== title ? (
          <p className="flight-popup-id muted">ID: {info.id}</p>
        ) : null}
      </header>

      <section className="flight-popup-section">
        <h4 className="flight-popup-section-title">Route</h4>
        <DetailRow label="Route" value={info.route} />
        <DetailRow label="Origin" value={info.originCountry} />
        <DetailRow label="Status" value={info.status} />
      </section>

      {(Number.isFinite(flightValue) || Number.isFinite(displayCargoTotal)) && (
        <section className="flight-popup-section flight-popup-section--value">
          <h4 className="flight-popup-section-title">Value</h4>
          {Number.isFinite(flightValue) ? (
            <DetailRow label="Flight revenue" value={formatCurrency(flightValue, currency)} />
          ) : null}
          {Number.isFinite(displayCargoTotal) ? (
            <DetailRow label="Cargo on board" value={formatCurrency(displayCargoTotal, currency)} />
          ) : null}
          {showTotal ? (
            <DetailRow
              label="Total at risk"
              value={formatCurrency(totalAtRisk, currency)}
              strong
            />
          ) : null}
        </section>
      )}

      {cargo.length > 0 ? (
        <section className="flight-popup-section">
          <h4 className="flight-popup-section-title">Cargo on board ({cargo.length})</h4>
          <ul className="flight-popup-list">
            {cargo.map((item) => {
              const attrs = item.attributes || {};
              const lineValue = cargoLineValue(attrs);
              const qty = attrs.quantity;
              const unit = attrs.unit_price_usd;
              const detail =
                Number.isFinite(Number(qty)) && Number.isFinite(Number(unit))
                  ? `${qty} × ${formatCurrency(unit, currency)}`
                  : null;
              return (
                <li key={item.id} className="flight-popup-list-item">
                  <div className="flight-popup-list-main">
                    <span className="flight-popup-list-title">
                      {formatCommodityLabel(attrs.commodity)}
                    </span>
                    {attrs.sku_ref ? (
                      <span className="flight-popup-list-meta muted">SKU ref: {attrs.sku_ref}</span>
                    ) : null}
                  </div>
                  <div className="flight-popup-list-side">
                    {detail ? <span className="muted">{detail}</span> : null}
                    {Number.isFinite(lineValue) ? (
                      <span className="flight-popup-list-value">
                        {formatCurrency(lineValue, currency)}
                      </span>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      {skus.length > 0 ? (
        <section className="flight-popup-section">
          <h4 className="flight-popup-section-title">Linked SKUs ({skus.length})</h4>
          <ul className="flight-popup-list">
            {skus.map((item) => {
              const attrs = item.attributes || {};
              const invValue = skuInventoryValue(attrs);
              return (
                <li key={item.id} className="flight-popup-list-item">
                  <div className="flight-popup-list-main">
                    <span className="flight-popup-list-title">{attrs.sku || item.id}</span>
                    <span className="flight-popup-list-meta muted">
                      {formatCommodityLabel(attrs.commodity)}
                      {attrs.warehouse_id ? ` · ${attrs.warehouse_id}` : ""}
                    </span>
                  </div>
                  <div className="flight-popup-list-side">
                    {Number.isFinite(Number(attrs.on_hand_qty)) ? (
                      <span className="muted">{attrs.on_hand_qty} on hand</span>
                    ) : null}
                    {Number.isFinite(invValue) ? (
                      <span className="flight-popup-list-value">
                        {formatCurrency(invValue, currency)}
                      </span>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      {isHighlighted ? (
        <footer className="flight-popup-footer">
          <span className="flight-popup-affected">Affected by scenario</span>
        </footer>
      ) : null}
    </div>
  );
}

FlightEntityPopup.propTypes = {
  info: PropTypes.shape({
    id: PropTypes.string,
    callSign: PropTypes.string,
    route: PropTypes.string,
    originCountry: PropTypes.string,
    status: PropTypes.string,
    companyId: PropTypes.string,
    companyName: PropTypes.string,
    revenueUsd: PropTypes.number,
    valueUsd: PropTypes.number,
  }).isRequired,
  valueByEntity: PropTypes.instanceOf(Map).isRequired,
  affectedIds: PropTypes.arrayOf(PropTypes.string).isRequired,
  currency: PropTypes.string.isRequired,
  supplyChainIndexes: PropTypes.shape({
    cargoByCarrier: PropTypes.instanceOf(Map),
    skusByCarrier: PropTypes.instanceOf(Map),
  }),
  isHighlighted: PropTypes.bool,
};
