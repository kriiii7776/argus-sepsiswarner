# SepsisGuard AI Security Architecture

This document outlines the security architecture and mechanisms designed for SepsisGuard AI. This prototype architecture is designed to be highly secure, protecting sensitive patient data while allowing for seamless adaptation to specific institutional security requirements (e.g., HIPAA, GDPR, or specific hospital IT policies) in the future.

## 1. Identity & Access Management (IAM)

### 1.1 Authentication (AuthN)
*   **Mechanism**: JSON Web Tokens (JWT) combined with OAuth 2.0 / OpenID Connect (OIDC).
*   **Integration**: Designed to act as a Service Provider integrating with institutional Identity Providers (IdP) such as Active Directory, Okta, or Ping Identity via SAML or OIDC. For the prototype phase, a local secure mock-IdP is used.
*   **Multi-Factor Authentication (MFA)**: Mandatory for all administrative and remote access roles. Highly recommended for clinical staff accessing the system from outside the secure hospital network.
*   **Session Management**: Short-lived access tokens (e.g., 15-30 minutes) with longer-lived, securely stored refresh tokens. Absolute session timeouts and idle timeouts are enforced.

### 1.2 Authorization (AuthZ) & Role-Based Access Control (RBAC)
Authorization is enforced at both the API gateway and individual service levels using a strict Role-Based Access Control (RBAC) model. Access to endpoints and data resources is determined by the roles embedded in the authenticated user's JWT.

#### Defined Roles and Permissions

1.  **ICU Nurse**:
    *   *Permissions*: View real-time sepsis risk scores, alerts, and immediate clinical context (current vitals, recent labs) for assigned patients only. Input basic clinical observations.
    *   *Restrictions*: Cannot access complete historical medical records outside the current admission. Cannot view system configurations.
2.  **Doctor**:
    *   *Permissions*: View comprehensive patient data, detailed sepsis risk trajectories, model explainability features (SHAP values), and historical clinical data for patients under their care. Can acknowledge, dismiss, or annotate alerts.
    *   *Restrictions*: Cannot modify system configurations, manage user roles, or access underlying model code/infrastructure.
3.  **Administrator (Clinical/Operational)**:
    *   *Permissions*: Manage clinical user accounts and role assignments. Configure operational thresholds (e.g., alert sensitivity rules for specific wards). View aggregated system usage reports.
    *   *Restrictions*: **Cannot view identified patient clinical data.** Cannot modify system infrastructure or core ML models.
4.  **ML Engineer**:
    *   *Permissions*: Access model performance metrics, aggregate prediction statistics, and model versioning tools. Deploy new model versions to staging environments. Access pseudonymized/anonymized inference logs for model monitoring.
    *   *Restrictions*: **Zero access to raw, identified patient data (PHI/PII)** in the production environment. No access to production transactional databases.
5.  **System Administrator**:
    *   *Permissions*: Manage network configurations, infrastructure deployment, database instances, secrets management (HashiCorp Vault), and system-level audit logs.
    *   *Restrictions*: Routine access to patient data applications is blocked. Access to databases containing PHI is heavily audited, restricted, and requires "break-glass" procedures.

## 2. Data Protection

### 2.1 Encryption
*   **In Transit**: All communication between clients, the API gateway, internal microservices, and databases MUST be encrypted using TLS 1.3. Plaintext HTTP communication is strictly prohibited and actively blocked.
*   **At Rest**: All databases, persistent storage volumes, and backups containing sensitive data are encrypted using AES-256 encryption. Database-level encryption (e.g., Transparent Data Encryption - TDE) is utilized for relational stores.

### 2.2 Data Minimization & Pseudonymization
*   **Principle of Least Privilege**: The UI and backend APIs are designed to serve only the absolute minimum data necessary for the user's specific role and current task.
*   **Pseudonymization Engine**: A dedicated middleware service intercepts data destined for ML monitoring or analytics. It strips Direct Identifiers (names, exact birthdates, MRNs) and replaces them with secure, one-way hashed pseudonyms before the data leaves the secure clinical boundary.
*   **Feature Isolation**: Predictive models are trained and infer exclusively on clinical features (e.g., heart rate, lactate levels) without requiring direct patient identifiers, ensuring the model itself does not process or memorize PHI.

## 3. Infrastructure & Network Security

### 3.1 Secure API Communication
*   **API Gateway**: All external traffic routes through a centralized API Gateway. The gateway handles TLS termination, rate limiting (DDoS mitigation), payload size restrictions, and initial JWT signature validation.
*   **Service Mesh / mTLS**: Communication between internal microservices utilizes mutual TLS (mTLS). This ensures that services securely authenticate each other, preventing internal lateral movement if a single service is compromised.

### 3.2 Secrets Management
*   **Centralized Vault**: Hardcoded secrets in code or environment variables are strictly prohibited. A centralized secure vault (e.g., HashiCorp Vault) dynamically injects database credentials, API keys, and cryptographic keys into services at runtime.
*   **Dynamic Rotation**: Database passwords and internal service tokens are automatically rotated on a regular schedule (e.g., every 30 days) by the secrets manager.

### 3.3 Database Security
*   **Network Isolation**: All datastores reside in deeply isolated private subnets with no direct ingress or egress to the public internet.
*   **Least Privilege Accounts**: Application microservices connect to databases using unique service accounts that only have permissions (SELECT, INSERT, UPDATE) for the specific tables they require.

## 4. Monitoring, Auditing, and Response

### 4.1 Audit & Access Logging
*   **Comprehensive Logging**: The system logs all authentication attempts (success/failure), authorization decisions, API requests, and data access events. **Viewing a patient's record generates a mandatory, indelible audit log entry.**
*   **Log Integrity**: Logs are forwarded in real-time to a centralized, append-only, immutable SIEM (Security Information and Event Management) system.
*   **Traceability**: Every log entry includes a synchronized timestamp, user ID (or service ID), requested resource, action taken, and origin IP address.

### 4.2 Backup and Recovery
*   **Automated Backups**: Automated, encrypted backups of all databases and infrastructure states are taken daily.
*   **Air-gapped Storage**: Backups are replicated to a geographically separate, heavily restricted "air-gapped" storage location to protect against ransomware.
*   **Testing**: Disaster recovery (DR) and restoration procedures are formally tested and validated at least bi-annually.

### 4.3 Incident Response
*   The architecture integrates with automated alerting systems. Alerts are triggered in the SIEM for suspicious activities such as impossible travel logins, mass data extraction attempts, or repeated unauthorized access attempts.
*   The design supports rapid isolation of compromised microservices or network segments without bringing down the entire platform.

## 5. Model Security (MLSecOps)

### 5.1 Model Access Control
*   **Inference API Isolation**: The model inference engine is exposed strictly as an internal microservice, accessible only by the primary backend API. Direct external access to the inference endpoints is impossible.
*   **Artifact Security**: Saved model weights (e.g., `.pkl`, `.pt` files) are stored in secure object storage with strict IAM policies. Only the CI/CD pipeline and the production inference service have read access.
*   **Input Validation**: The API Gateway and application logic perform rigorous bounds checking and input validation on clinical data before it is sent to the model to mitigate adversarial input attacks designed to skew predictions.
