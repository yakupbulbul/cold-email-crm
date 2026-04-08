import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.K6_BASE_URL || "http://127.0.0.1:8060";
const EMAIL = __ENV.K6_ADMIN_EMAIL || "admin@example.com";
const PASSWORD = __ENV.K6_ADMIN_PASSWORD || "";

export const options = {
  stages: [
    { duration: "20s", target: 5 },
    { duration: "20s", target: 15 },
    { duration: "20s", target: 30 },
    { duration: "20s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<2500"],
  },
};

function getToken() {
  const response = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(response, { "stress login ok": (res) => res.status === 200 });
  return response.json("access_token");
}

export default function () {
  const token = getToken();
  const params = { headers: { Authorization: `Bearer ${token}` } };

  const responses = http.batch([
    ["GET", `${BASE_URL}/api/v1/domains`, null, params],
    ["GET", `${BASE_URL}/api/v1/mailboxes`, null, params],
    ["GET", `${BASE_URL}/api/v1/ops/health`, null, params],
    ["GET", `${BASE_URL}/api/v1/ops/readiness`, null, params],
  ]);

  responses.forEach((response) => {
    check(response, { "stress request completed": (res) => res.status === 200 });
  });
}
