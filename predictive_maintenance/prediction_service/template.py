RUL_TEMPLATE = {
    "instruction": (
        "You are an expert in predictive maintenance and remaining useful life (RUL) estimation "
        "for electrical and lighting systems."
    ),

    "input": """The historical condition data for device {device_id} is shown below.
        The data is sampled every {data_frequency} minutes.

        Historical time range:
        - Start time: {start_timestamp}
        - End time: {end_timestamp}

        Historical sensor and control data:
        {input_series}

        Additional derived indicators (rolling & lag features):
        {additional_data_content}

        Task:
        Based on the historical data and degradation patterns, predict the RUL (Remaining Useful Life) 
        for the NEXT time step only ({prediction_timestamp}). Return ONLY a single integer number (no explanation).

        Notes:
        - RUL is measured in hours.
        - Do not include explanations or units.
        - The average RUL hour of the LED is 1000 hours.
        - RUL is expected to be decreasing over time.
        - Assume the LED consumes at least 1 hour of RUL every 1 hour even under stable operating conditions.
        - Sudden increases in RUL are unlikely unless operating stress is reduced.
        """,

    "output": "{predicted_rul}"
}
