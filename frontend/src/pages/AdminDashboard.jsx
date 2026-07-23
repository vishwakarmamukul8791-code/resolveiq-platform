import { useMemo, useState } from "react";
import * as XLSX from "xlsx";

import "../styles/admin-dashboard.css";


const usageData = [

    {
        name: "Mukul Vishwakarma",
        employeeId: "EMP1024",
        department: "AI / ML",
        loginDate: "18 Jul 2026",
        loginTime: "09:42 AM",
        logoutDate: "18 Jul 2026",
        logoutTime: "06:58 PM",
        sessionTime: "9h 16m",
        questions: 42,
        avgResponse: "2.4s",
        resolutions: 18,
        searches: 31,
        helpful: 36,
        status: "Completed"
    },

    {
        name: "Ankit Sharma",
        employeeId: "EMP1042",
        department: "Support",
        loginDate: "18 Jul 2026",
        loginTime: "10:05 AM",
        logoutDate: "18 Jul 2026",
        logoutTime: "07:12 PM",
        sessionTime: "9h 07m",
        questions: 38,
        avgResponse: "2.8s",
        resolutions: 22,
        searches: 29,
        helpful: 31,
        status: "Completed"
    },

    {
        name: "Priya Singh",
        employeeId: "EMP1088",
        department: "Support",
        loginDate: "18 Jul 2026",
        loginTime: "09:56 AM",
        logoutDate: "18 Jul 2026",
        logoutTime: "05:45 PM",
        sessionTime: "7h 49m",
        questions: 27,
        avgResponse: "2.1s",
        resolutions: 14,
        searches: 19,
        helpful: 24,
        status: "Completed"
    },

    {
        name: "Rahul Mehta",
        employeeId: "EMP1092",
        department: "Operations",
        loginDate: "18 Jul 2026",
        loginTime: "11:15 AM",
        logoutDate: "-",
        logoutTime: "-",
        sessionTime: "Active",
        questions: 19,
        avgResponse: "3.2s",
        resolutions: 8,
        searches: 16,
        helpful: 15,
        status: "Active"
    },

    {
        name: "Sneha Kapoor",
        employeeId: "EMP1114",
        department: "Support",
        loginDate: "18 Jul 2026",
        loginTime: "10:21 AM",
        logoutDate: "18 Jul 2026",
        logoutTime: "04:52 PM",
        sessionTime: "6h 31m",
        questions: 21,
        avgResponse: "2.7s",
        resolutions: 11,
        searches: 17,
        helpful: 18,
        status: "Completed"
    }

];


function AdminDashboard() {

    const [period, setPeriod] = useState("month");

    const [search, setSearch] = useState("");


    const filteredUsers = useMemo(() => {

        return usageData.filter((user) =>

            user.name.toLowerCase().includes(search.toLowerCase()) ||

            user.employeeId.toLowerCase().includes(search.toLowerCase()) ||

            user.department.toLowerCase().includes(search.toLowerCase())

        );

    }, [search]);


    const handleExport = () => {

        const excelData = usageData.map((user) => ({

            "Employee Name": user.name,

            "Employee ID": user.employeeId,

            "Department": user.department,

            "Login Date": user.loginDate,

            "Login Time": user.loginTime,

            "Logout Date": user.logoutDate,

            "Logout Time": user.logoutTime,

            "Total Session Time": user.sessionTime,

            "Questions Asked": user.questions,

            "Average Response Time": user.avgResponse,

            "Resolutions Viewed": user.resolutions,

            "Search Count": user.searches,

            "Helpful Answers": user.helpful,

            "Session Status": user.status

        }));


        const worksheet = XLSX.utils.json_to_sheet(excelData);

        const workbook = XLSX.utils.book_new();


        XLSX.utils.book_append_sheet(

            workbook,

            worksheet,

            "Employee Usage"

        );


        XLSX.writeFile(

            workbook,

            `incident-ai-usage-${period}.xlsx`

        );

    };


    return (

        <div className="admin-dashboard">


            <header className="admin-header">

                <div>

                    <span className="admin-eyebrow">
                        ADMINISTRATION
                    </span>

                    <h1>
                        System overview.
                    </h1>

                    <p>
                        Monitor Incident AI adoption and support productivity.
                    </p>

                </div>


                <div className="admin-header-actions">

                    <button className="admin-user">
                        ADMIN
                    </button>

                </div>

            </header>


            <main className="admin-content">


                {/* KPI CARDS */}

                <section className="admin-kpi-grid">


                    <div className="admin-kpi-card">

                        <span>
                            ACTIVE ENGINEERS
                        </span>

                        <strong>
                            24
                        </strong>

                        <p className="positive">
                            ↑ 12.5% this month
                        </p>

                    </div>


                    <div className="admin-kpi-card">

                        <span>
                            QUESTIONS ASKED
                        </span>

                        <strong>
                            8,492
                        </strong>

                        <p className="positive">
                            ↑ 18.2% this month
                        </p>

                    </div>


                    <div className="admin-kpi-card">

                        <span>
                            AVG SESSION TIME
                        </span>

                        <strong>
                            6h 42m
                        </strong>

                        <p>
                            Across all engineers
                        </p>

                    </div>


                    <div className="admin-kpi-card">

                        <span>
                            AVG QUESTIONS / USER
                        </span>

                        <strong>
                            35.4
                        </strong>

                        <p className="positive">
                            ↑ 8.7% this month
                        </p>

                    </div>

                </section>


                {/* USAGE OVERVIEW */}

                <section className="admin-panel usage-overview">


                    <div className="panel-heading">

                        <div>

                            <span className="section-label">
                                USAGE OVERVIEW
                            </span>

                            <h2>
                                Platform adoption
                            </h2>

                        </div>


                        <div className="period-selector">

                            <button
                                className={period === "day" ? "selected" : ""}
                                onClick={() => setPeriod("day")}
                            >
                                Day
                            </button>

                            <button
                                className={period === "week" ? "selected" : ""}
                                onClick={() => setPeriod("week")}
                            >
                                Week
                            </button>

                            <button
                                className={period === "month" ? "selected" : ""}
                                onClick={() => setPeriod("month")}
                            >
                                Month
                            </button>

                            <button
                                className={period === "year" ? "selected" : ""}
                                onClick={() => setPeriod("year")}
                            >
                                Year
                            </button>

                        </div>

                    </div>


                    <div className="usage-chart">

                        <div className="chart-bar bar-one">
                            <span>Mon</span>
                        </div>

                        <div className="chart-bar bar-two">
                            <span>Tue</span>
                        </div>

                        <div className="chart-bar bar-three">
                            <span>Wed</span>
                        </div>

                        <div className="chart-bar bar-four">
                            <span>Thu</span>
                        </div>

                        <div className="chart-bar bar-five">
                            <span>Fri</span>
                        </div>

                        <div className="chart-bar bar-six">
                            <span>Sat</span>
                        </div>

                        <div className="chart-bar bar-seven">
                            <span>Sun</span>
                        </div>

                    </div>

                </section>


                {/* EMPLOYEE USAGE */}

                <section className="admin-panel employee-panel">


                    <div className="panel-heading">

                        <div>

                            <span className="section-label">
                                EMPLOYEE USAGE
                            </span>

                            <h2>
                                Support engineer activity
                            </h2>

                        </div>


                        <button
                            className="export-button"
                            onClick={handleExport}
                        >
                            ↓ Export Excel
                        </button>

                    </div>


                    <div className="table-toolbar">

                        <input
                            type="text"
                            placeholder="Search employee or department..."
                            value={search}
                            onChange={(event) => setSearch(event.target.value)}
                        />

                        <span>
                            Showing {filteredUsers.length} engineers
                        </span>

                    </div>


                    <div className="table-wrapper">

                        <table>

                            <thead>

                                <tr>

                                    <th>EMPLOYEE</th>

                                    <th>DEPARTMENT</th>

                                    <th>LOGIN</th>

                                    <th>LOGOUT</th>

                                    <th>SESSION</th>

                                    <th>QUESTIONS</th>

                                    <th>AVG RESPONSE</th>

                                    <th>STATUS</th>

                                </tr>

                            </thead>


                            <tbody>

                                {filteredUsers.map((user) => (

                                    <tr key={user.employeeId}>

                                        <td>

                                            <div className="employee-name">

                                                <div className="employee-avatar">
                                                    {user.name.charAt(0)}
                                                </div>

                                                <div>

                                                    <strong>
                                                        {user.name}
                                                    </strong>

                                                    <span>
                                                        {user.employeeId}
                                                    </span>

                                                </div>

                                            </div>

                                        </td>


                                        <td>
                                            {user.department}
                                        </td>


                                        <td>
                                            {user.loginTime}
                                        </td>


                                        <td>
                                            {user.logoutTime}
                                        </td>


                                        <td>
                                            {user.sessionTime}
                                        </td>


                                        <td className="question-count">
                                            {user.questions}
                                        </td>


                                        <td>
                                            {user.avgResponse}
                                        </td>


                                        <td>

                                            <span
                                                className={
                                                    user.status === "Active"
                                                        ? "status active"
                                                        : "status completed"
                                                }
                                            >
                                                {user.status}
                                            </span>

                                        </td>

                                    </tr>

                                ))}

                            </tbody>

                        </table>

                    </div>

                </section>

            </main>

        </div>

    );

}

export default AdminDashboard;