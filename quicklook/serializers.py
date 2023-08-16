from rest_framework import serializers, fields
from .models import QuickLookResults, QuickLookQuery


class QuickLookQuerySerializer(serializers.ModelSerializer):
    land_purchase_date = fields.DateField(input_formats=["%Y-%m-%d"])
    building_sale = fields.DateField(input_formats=["%Y-%m-%d"])
    mass_grading_start = fields.DateField(input_formats=["%Y-%m-%d"])

    class Meta:
        model = QuickLookQuery
        fields = (
            "pk",
            "name",
            "region",
            "date",
            "land_purchase_date",
            "building_sale",
            "mass_grading_start",
            "total_area",
            "rent_per_unit_area",
            "exit_cap",
            "land_cost",
            "building_hard_cost",
            "building_soft_cost",
            "tenant_improvements",
            "cash_contributions",
            "rent_free_period",
            "lease_up_period",
        )


class QuickLookResultsSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickLookResults
        fields = (    
            "pk",       
            "unlevered_irr",
            "unlevered_mult",
            "yoc",
            "ncf",
            "unl_costs",
            "lev_costs",
            "unl_peak_equity",
            "gross_sale_price",
            "net_sale_price",
        )
