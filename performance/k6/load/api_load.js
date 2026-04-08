import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.K6_BASE_URL || "http://127.0.0.1:8060";
const EMAIL = __ENV.K6_ADMIN_EMAIL || "admin@example.com";
const PASSWORD = __ENV.K6_ADMIN_PASSWORD || "";

export const options = {
  stages: [
    { duration: "30s", target: 5 },
    { duration: "1m", target: 5 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.02"],
    http_req_duration: ["p(95)<1500"],
  },
};

function authParams() {
  const login = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(login, { "login ok": (res) => res.status === 200 });
  return { headers: { Authorization: `Bearer ${login.json("access_token")}` } };
}

export default function () {
  const params = authParams();
  const responses = http.batch([
    ["GET", `${BASE_URL}/api/v1/domains`, null, params],
    ["GET", `${BASE_URL}/api/v1/mailboxes`, null, params],
    ["GET", `${BASE_URL}/api/v1/settings/summary`, null, params],
    ["GET", `${BASE_URL}/api/v1/ops/health`, null, params],
  ]);

  responses.forEach((response) => {
    check(response, { "load request succeeded": (res) => res.status === 200 });
  });

  sleep(1);
}
