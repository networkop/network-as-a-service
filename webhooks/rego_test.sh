#!/bin/bash
opa test ./webhooks/main.rego ./webhooks/validate.rego ./webhooks/validate_test.rego  -v