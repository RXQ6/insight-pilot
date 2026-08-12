package com.insightpilot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "eval_cases")
@Getter
@Setter
@NoArgsConstructor
public class EvalCase {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(length = 32)
    private String type;

    @Column(columnDefinition = "text")
    private String question;

    @Column(name = "expected_sql", columnDefinition = "text")
    private String expectedSql;

    @Column(name = "expected_summary", columnDefinition = "text")
    private String expectedSummary;

    @Column(length = 16)
    private String difficulty;
}
