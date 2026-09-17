"""Role definitions and the RBAC permission matrix."""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ARTISAN = "ARTISAN"
    BUYER = "BUYER"
    B2B_BUYER = "B2B_BUYER"
    CLUSTER_MANAGER = "CLUSTER_MANAGER"
    ADMIN = "ADMIN"


# Coarse-grained matrix; fine-grained ownership checks live in dependencies.
PERMISSIONS: dict[str, set[Role]] = {
    "products:create": {Role.ARTISAN},
    "products:update_own": {Role.ARTISAN},
    "orders:create": {Role.BUYER, Role.B2B_BUYER},
    "orders:fulfil_own": {Role.ARTISAN},
    "reviews:create": {Role.BUYER, Role.B2B_BUYER},
    "bulk_request:create": {Role.BUYER, Role.B2B_BUYER},
    "quotes:create_own": {Role.ARTISAN},
    "analytics:own": {Role.ARTISAN, Role.B2B_BUYER},
    "analytics:cluster": {Role.CLUSTER_MANAGER},
    "admin:*": {Role.ADMIN},
    "clusters:manage": {Role.CLUSTER_MANAGER, Role.ADMIN},
}
