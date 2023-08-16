from .ro_utils import DealValues, KeyDates, QuicklookInputs
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
import datetime

from .models import QuickLookQuery
from .serializers import *


@api_view(["GET", "POST"])
def quick_look_analysis(request):
    if request.method == "GET":
        data = QuickLookQuery.objects.all()

        serializer = QuickLookQuerySerializer(
            data, context={"request": request}, many=True
        )

        return Response(serializer.data)

    elif request.method == "POST":
        serializer = QuickLookQuerySerializer(data=request.data)
        print(request.data)
        if serializer.is_valid():
            serializer.save()
            data = serializer.data
            format = "%Y-%m-%d"
            """
            In input data, ensure date days are set to 1. This is to maintain consistency.1
            """
            input_data = QuicklookInputs(
                name=data["name"],
                key_dates=KeyDates(
                    land_purchase_date=datetime.datetime.strptime(
                        data["land_purchase_date"], format
                    ).replace(day=1),
                    building_sale=datetime.datetime.strptime(
                        data["building_sale"], format
                    ).replace(day=1),
                    mass_grading_start=datetime.datetime.strptime(
                        data["mass_grading_start"], format
                    ).replace(day=1),
                    rent_free_period=data["rent_free_period"],
                    lease_up_period=data["lease_up_period"],
                ),
                values=DealValues(
                    region=data["region"],
                    total_area=data["total_area"],
                    rent_per_unit_area=data["rent_per_unit_area"],
                    exit_cap=data["exit_cap"],
                    land_cost=data["land_cost"],
                    building_hard_cost=data["building_hard_cost"],
                    building_soft_cost=data["building_soft_cost"],
                    tenant_improvements=data["tenant_improvements"],
                    cash_contributions=data["cash_contributions"],
                ),
            )

            results = QuickLookResults(
                unlevered_irr=input_data.unlevered_irr(),
                unlevered_mult=input_data.unlevered_em(),
                yoc=input_data.yoc(),
                ncf=input_data.unlevered_ncf(),
                unl_costs=input_data.total_unlevered_cost(),
                lev_costs=input_data.total_levered_cost(),
                unl_peak_equity=input_data.unlevered_peak_equity(),
                net_sale_price=input_data.net_sale_price(),
                gross_sale_price=input_data.values.gross_sale_price,
            )

            serializer = QuickLookResultsSerializer(results)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
