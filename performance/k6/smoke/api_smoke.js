import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.K6_BASE_URL || "http://127.0.0.1:8060";
const EMAIL = __ENV.K6_ADMIN_EMAIL || "admin@example.com";
const PASSWORD = __ENV.K6_ADMIN_PASSWORD || "";

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
  },
};

function login() {
  const response = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(response, { "login succeeded": (res) => res.status === 200 });
  return response.json("access_token");
}

export default function () {
  const token = login();
  const params = { headers: { Authorization: `Bearer ${token}` } };

  const authMe = http.get(`${BASE_URL}/api/v1/auth/me`, params);
  const domains = http.get(`${BASE_URL}/api/v1/domains`, params);
  const mailboxes = http.get(`${BASE_URL}/api/v1/mailboxes`, params);
  const health = http.get(`${BASE_URL}/api/v1/ops/health`, params);

  check(authMe, { "auth/me healthy": (res) => res.status === 200 });
  check(domains, { "domains healthy": (res) => res.status === 200 });
  check(mailboxes, { "mailboxes healthy": (res) => res.status === 200 });
  check(health, { "ops health healthy": (res) => res.status === 200 });

  sleep(1);
}
