import datetime
import pandas as pd
import numpy as np
from dataclasses import dataclass
from pyxirr import xirr
from datetime import date
from enum import Enum
from dateutil.relativedelta import relativedelta
import numpy_financial as npf

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.float_format", "{:.0f}".format)


class KeyDates:
    def __init__(
        self,
        land_purchase_date,
        mass_grading_start,
        building_sale,
        rent_free_period,
        lease_up_period,
    ):
        """
        CORE ASSUMPTIONS
        """
        MASS_GRADING_LENGTH = 2
        VERTICAL_CONSTRUCTION_LENGTH = 8

        self.land_purchase_date = land_purchase_date
        self.mass_grading_start = mass_grading_start
        self.mass_grading_end = mass_grading_start + relativedelta(
            months=MASS_GRADING_LENGTH
        )
        self.vertical_construction_begin = self.mass_grading_end
        self.vertical_construction_end = (
            self.vertical_construction_begin
            + relativedelta(months=VERTICAL_CONSTRUCTION_LENGTH)
        )
        self.building_sale = building_sale
        self.rent_start_estimate = self.vertical_construction_end + relativedelta(
            months=(rent_free_period + lease_up_period)
        )
        self.rent_end_estimate = self.building_sale


@dataclass
class DealValues:
    def __init__(
        self,
        exit_cap,
        building_hard_cost,
        building_soft_cost,
        tenant_improvements,
        cash_contributions,
        land_cost,
        total_area,
        rent_per_unit_area,
        region,
    ):
        self.region = region
        self.rent_per_unit_area = rent_per_unit_area
        """
        Handle whether monthly or annual rent is used
        """
        if region == "UK":
            annual_rent = total_area * rent_per_unit_area
        elif region == "US":
            annual_rent = total_area * rent_per_unit_area
        elif region == "Poland":
            annual_rent = total_area * rent_per_unit_area * 12
        elif region == "Germany":
            annual_rent = total_area * rent_per_unit_area * 12
        else:
            annual_rent = 0
        self.annual_rent = annual_rent
        self.exit_cap = exit_cap / 100
        self.total_area = total_area
        self.building_hard_cost = building_hard_cost * total_area
        self.building_soft_cost = building_soft_cost * total_area
        self.cash_contributions = cash_contributions

        """
        CORE ASSUMPTIONS
        """

        TENANT_REP_COMMISSION_PC = 0.265
        LANDLORD_REP_COMMISSION_PC = 0.017
        EXPENSE_SLIPPAGE_PC = 0.017
        DEVELOPMENT_FEE_PC = 0.04

        if region == "UK":
            DEBT_FEES_PC = 0.11
            DISPOSITION_PC = 0.0935
        else:
            DEBT_FEES_PC = 0.038
            DISPOSITION_PC = 0.05
    
        self.total_levered_cost_multiple = DEBT_FEES_PC
        self.tenant_improvements = tenant_improvements * total_area
        self.tenant_rep_commission = annual_rent * TENANT_REP_COMMISSION_PC
        self.landlord_rep_commission = annual_rent * LANDLORD_REP_COMMISSION_PC
        self.expense_slippage = (
            self.building_hard_cost + self.building_soft_cost
        ) * EXPENSE_SLIPPAGE_PC
        self.land_cost = land_cost
        self.development_fee = (
            self.building_soft_cost + self.building_hard_cost
        ) * DEVELOPMENT_FEE_PC
        self.gross_sale_price = annual_rent / self.exit_cap
        self.disposition_cost = self.gross_sale_price * DISPOSITION_PC


@dataclass
class Budget:
    """
    A line item considered as a cost

    This class is used for line items that are split evenly over a period based on an overal cost

    Parameters
    ----------
    name : string
        The name of the line item, to be used in dataframe too
    start : int
        The month in which the first payment for cost is made
    end: int
        The month in which the last payment for cost is made
    budget: float
        The total budget for the cost
    """

    name: str
    start: datetime
    end: datetime
    budget: float


def apply_budget(data, budget: Budget):
    """
    Add a cost to line item that is equally split over the start and end date of the cost spread

    Given:
    * Budget, has a name, start, end and budget

    """
    data[budget.name] = np.zeros(len(data))

    budget_length = (
        (budget.end.year - budget.start.year) * 12
        + (budget.end.month - budget.start.month)
        + 1
    )

    data.loc[
        (data["Date"] <= budget.end) & (data["Date"] >= budget.start), budget.name
    ] = (-budget.budget / budget_length)


def add_income(data, income: Budget):
    """
    Add a cost to line item that is equally split over the start and end date of the cost spread

    Given:
    * Budget, has a name, start, end and budget

    """
    data[income.name] = np.zeros(len(data))
    data.loc[
        (data["Date"] <= income.end) & (data["Date"] >= income.start), income.name
    ] = income.budget


@dataclass
class QuicklookInputs:
    name: str
    key_dates: KeyDates
    values: DealValues

    def cash_flow_dates(self):
        """
        Generate date array for the cash flow which is 180 months = 15 years long
        """

        return pd.date_range(
            start=date.today() - relativedelta(months=50), periods=120 + 1, freq="MS"
        )

    def annual_rental_income(self):
        """
        Multiply area by rent per area
        """

        if self.values.total_area <= 0:
            return ValueError("Total area must be greater than 0")

        elif self.values.rent_per_unit_area <= 0:
            return ValueError("Rent must be greater than 0")

        else:
            return self.values.annual_rent

    def monthly_rental_income(self):
        """
        Divide the annual rental income by 12
        """
        try:
            return self.annual_rental_income() / 12
        except:
            return 0

    def uses_cash_flow(self):
        # ===============================================================================
        # LAND PURCHASE
        # ===============================================================================

        """
        Initialise dataframe with dates
        """

        df = pd.DataFrame(self.cash_flow_dates(), columns=["Date"])

        """
        Add Land Purchase, initialize with zeroes 
        """

        df["Land Purchase"] = np.zeros(len(df))

        """
        Add Land Purchase to land purchase date
        """
        df.loc[
            (df["Date"].dt.year == self.key_dates.land_purchase_date.year)
            & (df["Date"].dt.month == self.key_dates.land_purchase_date.month),
            "Land Purchase",
        ] = -self.values.land_cost

        # ===============================================================================
        # DEVELOPMENT and BUILD COSTS
        # ===============================================================================

        df["Mass Grading"] = np.zeros(len(df))
        df["Vertical Construction"] = np.zeros(len(df))
        df["Total Hard Cost"] = np.zeros(len(df))
        df["Building Soft Cost"] = np.zeros(len(df))
        df["Development Fee"] = np.zeros(len(df))
        MASS_GRADING_PROPORTION = 0.25
        mass_grading = self.values.building_hard_cost * MASS_GRADING_PROPORTION
        remaining_hard_costs = self.values.building_hard_cost - mass_grading

        """
        Apply all of the costs to the cash flow. (See apply_budget for more detail on the function)

        Given the 
        *start date 
        and 
        *end date
        
        for which that cost is incurred the function splits the cost evenly over those months. 
        """

        apply_budget(
            data=df,
            budget=Budget(
                name="Mass Grading",
                start=self.key_dates.mass_grading_start,
                end=self.key_dates.mass_grading_end,
                budget=mass_grading,
            ),
        )

        apply_budget(
            data=df,
            budget=Budget(
                name="Vertical Construction",
                start=self.key_dates.vertical_construction_begin,
                end=self.key_dates.vertical_construction_end,
                budget=remaining_hard_costs,
            ),
        )

        apply_budget(
            data=df,
            budget=Budget(
                name="Building Soft Cost",
                start=self.key_dates.land_purchase_date,
                end=self.key_dates.mass_grading_start,
                budget=self.values.building_soft_cost,
            ),
        )

        apply_budget(
            data=df,
            budget=Budget(
                name="Tenant Improvements",
                start=self.key_dates.rent_start_estimate,
                end=self.key_dates.rent_start_estimate + relativedelta(months=1),
                budget=self.values.tenant_improvements,
            ),
        )

        apply_budget(
            data=df,
            budget=Budget(
                name="Tenant Rep Commission",
                start=self.key_dates.rent_start_estimate,
                end=self.key_dates.rent_start_estimate + relativedelta(months=1),
                budget=self.values.tenant_rep_commission,
            ),
        )

        apply_budget(
            data=df,
            budget=Budget(
                name="Landlord Rep Commission",
                start=self.key_dates.rent_start_estimate,
                end=self.key_dates.rent_start_estimate + relativedelta(months=1),
                budget=self.values.landlord_rep_commission,
            ),
        )

        apply_budget(
            data=df,
            budget=Budget(
                name="Cash Contributions",
                start=self.key_dates.rent_start_estimate,
                end=self.key_dates.rent_start_estimate + relativedelta(months=1),
                budget=self.values.cash_contributions,
            ),
        )

        apply_budget(
            data=df,
            budget=Budget(
                name="Expense Slippage",
                start=self.key_dates.vertical_construction_end,
                end=self.key_dates.rent_start_estimate,
                budget=self.values.expense_slippage,
            ),
        )

        apply_budget(
            data=df,
            budget=Budget(
                name="Development Fee",
                start=self.key_dates.mass_grading_start,
                end=self.key_dates.vertical_construction_end,
                budget=self.values.development_fee,
            ),
        )

        """
        Sum up Total Hard Cost 
        """
        df["Total Hard Cost"] = df["Mass Grading"] + df["Vertical Construction"]

        """
        Sum up Total Unlevered Cost 
        """
        df["Total Unlevered Cost"] = (
            df["Land Purchase"]
            + df["Mass Grading"]
            + df["Vertical Construction"]
            + df["Development Fee"]
            + df["Building Soft Cost"]
            + df["Tenant Improvements"]
            + df["Tenant Rep Commission"]
            + df["Landlord Rep Commission"]
            + df["Expense Slippage"]
            + df["Cash Contributions"]
        )

        # ===============================================================================
        # RENTAL INCOME
        # ===============================================================================

        monthly_rental_income = self.monthly_rental_income()
        RENTAL_COSTS = 0.25
        net_rent = monthly_rental_income * (1 - RENTAL_COSTS)
        add_income(
            data=df,
            income=Budget(
                name="Rental Income",
                start=self.key_dates.rent_start_estimate,
                end=self.key_dates.rent_end_estimate,
                budget=net_rent,
            ),
        )

        # ===============================================================================
        # ASSET SALE
        # ===============================================================================

        """
        Initialise the columns for the cash flow. 
        """
        df["Building Sale"] = np.zeros(len(df))
        df["Disposition Cost"] = np.zeros(len(df))

        """
        Add Building Sale to cash flow
        
        Income reaches cash flow on land purchase date

        """
        df.loc[
            (df["Date"].dt.year == self.key_dates.building_sale.year)
            & (df["Date"].dt.month == self.key_dates.building_sale.month),
            "Building Sale",
        ] = self.values.gross_sale_price

        """
        Disposition costs are incurred on land purchase date
        """
        df.loc[
            (df["Date"].dt.year == self.key_dates.building_sale.year)
            & (df["Date"].dt.month == self.key_dates.building_sale.month),
            "Disposition Cost",
        ] = -self.values.disposition_cost

        """
        The total revenue comes from
        * Building Sale
        * Disposition Costs
        * Rental Income

        """
        df["Total Revenue"] = (
            df["Building Sale"] + df["Disposition Cost"] + df["Rental Income"]
        )

        df["Unlevered Cash Flow"] = df["Total Revenue"] + df["Total Unlevered Cost"]

        """
        Cumulative Cash Flow
        """
        df["Cum Unlevered Cash Flow"] = df["Unlevered Cash Flow"].cumsum()

        return df

    def unlevered_cash_flow(self):
        """
        Output
        ------
        The unlevered cash flow as a slice of the dataframe
        """

        return self.uses_cash_flow()["Unlevered Cash Flow"]

    def unlevered_ncf(self):
        """
        Output
        ------
        The sum of the unlvered cash flows
        """
        return self.uses_cash_flow()["Unlevered Cash Flow"].sum()

    def total_unlevered_cost(self):
        """
        Output
        ------
        The sum of all of the unlevered costs.
        """
        return self.uses_cash_flow()["Total Unlevered Cost"].sum()

    def total_levered_cost(self):
        """
        Output
        ------
        The levered costs multiplied by an estimator based on historical data
        """
        try:
            return self.total_unlevered_cost() * (
                1 + self.values.total_levered_cost_multiple
            )
        except:
            return 0

    def yoc(self):
        """
        Output
        ------
        The yield on estimated levered cost

        """

        if self.total_unlevered_cost() != 0:
            try:
                return -(self.annual_rental_income()) / (
                    self.total_unlevered_cost()
                    * (1 + self.values.total_levered_cost_multiple)
                )
            except:
                return 0
        else:
            return 0

    def unlevered_peak_equity(self):
        """
        Output
        ------
        The minimum value on the cumulative unlevered cash flow

        """
        return self.uses_cash_flow()["Cum Unlevered Cash Flow"].min()

    def net_sale_price(self):
        """
        Input
        -----
        * Building sale proceeds
        * Disposition Costs

        Output
        ------
        Net Sale Price

        """
        return (
            self.uses_cash_flow()["Disposition Cost"].sum()
            + self.uses_cash_flow()["Building Sale"].sum()
        )

    def unlevered_em(self):
        """
        Output
        ------
        The unlevered equity multiple

        """
        if self.unlevered_peak_equity() != 0:
            try:
                return (
                    -(self.unlevered_ncf() - self.unlevered_peak_equity())
                    / self.unlevered_peak_equity()
                )
            except:
                return 0
        else:
            return 0

    def unlevered_irr(self):
        """
        Output
        ------
        The unlevered IRR using PyXirr

        """
        dates = self.cash_flow_dates()
        values = self.unlevered_cash_flow()
        try:
            return xirr(dates, values)
        except:
            return 0

    def start_date_index(self):
        """
        Output
        ------
        The pandas index of the first land purchase month in the cash flow

        """
        df = self.uses_cash_flow()
        return df.index[df["Date"] == self.key_dates.land_purchase_date]

    def end_date_index(self):
        """
        Output
        ------
        The pandas index of the first land purchase month in the cash flow

        """
        df = self.uses_cash_flow()
        return df.index[df["Date"] == self.key_dates.building_sale]

    def unlevered_irr_numpy(self):
        """
        Output
        ------
        The unlevered IRR using numpy-financial

        """
        values = self.unlevered_cash_flow()[
            self.start_date_index() : self.end_date_index()
        ]
        try:
            return npf.irr(values) * 10
        except:
            return 0
