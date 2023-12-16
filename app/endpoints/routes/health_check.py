from flask_restx import Resource, Namespace

ns = Namespace("health_check", description="Endpoint for server health check", path="/api/health_check")


class HealthCheck(Resource):
    def get(self):
        return "ok", 200


ns.add_resource(HealthCheck, "", methods=["GET"])
