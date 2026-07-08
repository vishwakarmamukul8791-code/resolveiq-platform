def calculate_confidence(distances):

    if len(distances) == 0:
        return "Unknown", 0

    average_distance = sum(distances) / len(distances)

    if average_distance < 1.3:
        confidence = "High"

    elif average_distance < 2.0:
        confidence = "Medium"

    else:
        confidence = "Low"

    return confidence, round(average_distance, 3)