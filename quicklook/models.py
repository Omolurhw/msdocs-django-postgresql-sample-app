from django.db import models

class QuickLookQuery(models.Model):
    UK = "UK"
    POLAND = "Poland"
    GERMANY = "Germany"
    US = "US"
    REGIONS = [
        (UK, "UK"),
        (POLAND, "Poland"),
        (GERMANY, "Germany"),
        (US, "US"),
    ]
    name = models.CharField(max_length=240)
    land_purchase_date = models.DateField()
    region = models.CharField(max_length=240,
                              choices=REGIONS)
    date = models.DateTimeField(auto_now_add=True)
    building_sale = models.DateField()
    mass_grading_start = models.DateField()
    total_area = models.FloatField()
    rent_per_unit_area = models.FloatField()
    exit_cap = models.FloatField()
    land_cost = models.FloatField()
    building_hard_cost = models.FloatField()
    building_soft_cost = models.FloatField()
    tenant_improvements = models.FloatField()
    cash_contributions = models.FloatField()
    rent_free_period = models.IntegerField()
    lease_up_period = models.IntegerField()

class QuickLookResults(models.Model):
    unlevered_irr = models.FloatField("Unlevered IRR")
    unlevered_mult = models.FloatField("Unlevered EM")
    yoc = models.FloatField("Yield on Cost")
    ncf = models.FloatField("Net Cash Flow")
    unl_costs = models.FloatField("Total Unlevered Costs")
    lev_costs = models.FloatField("Total Levered Costs")
    unl_peak_equity = models.FloatField("Unlevered Peak Equity")
    net_sale_price = models.FloatField("Net Sale Price")
    gross_sale_price = models.FloatField("Gross Sale Price")